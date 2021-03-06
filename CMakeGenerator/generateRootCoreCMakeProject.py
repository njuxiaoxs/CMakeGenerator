#!/usr/bin/env python
#
# $Id: generateRootCoreCMakeProject.py 153234 2014-10-28 18:39:34Z krasznaa $
#
# Helper script for generating a CMake project file to help editing checked-out
# RootCore packages through the IDE project file that CMake in turn generates.
#

# Some often used modules:
import os
import glob

# Function executing a shell command and returning its printed output
def runCommand( command ):
    # First off, split the command into words:
    command_words = command.split()
    # Open /dev/null to suppress stderr messages:
    FNULL = open( os.devnull, "w" )
    # Run the command:
    import subprocess
    return subprocess.Popen( command_words,
                             stdout = subprocess.PIPE,
                             stderr = FNULL ).communicate()[ 0 ].strip()

# Function getting the path to the local test/working directory
def getWorkDir():
    # This is based on the $ROOTCOREBIN environment variable...
    bindir = os.environ[ "ROOTCOREBIN" ]
    # Which will end in either RootCore or RootCoreBin. Which needs to be
    # removed from the path.
    if bindir.find( "/RootCoreBin" ) == ( len( bindir ) -
                                          len( "/RootCoreBin" ) ):
        return bindir[ : - len( "/RootCoreBin" ) ]
    elif bindir.find( "/RootCore" ) == ( len( bindir ) -
                                         len( "/RootCore" ) ):
        return bindir[ : - len( "/RootCore" ) ]
    else:
        raise EnvironmentError( "Couldn't find RootCore work/test directory" )

# Function extracting path definitions from compiler/linker flags
def getFlags( flags, prefix ):
    # First off, split the flags into words:
    flag_words = flags.split()
    # Find the include definitions in it:
    extracted = []
    for flag in flag_words:
        if flag.find( prefix ) == 0:
            extracted += [ flag[ len( prefix ) : ] ]
            pass
        pass
    # Return the collected directories:
    return extracted

# Helper function for the getFiles(...) function
def getFilesHelper( directory, pattern ):
    for root, dirs, files in os.walk( directory ):
        for basename in files:
            import fnmatch
            if fnmatch.fnmatch( basename, pattern ):
                filename = os.path.join( root, basename )
                yield filename

# Get the file names matching a pattern, as a simple string
def getFiles( directory, pattern ):
    result = ""
    for filename in getFilesHelper( directory, pattern ):
        result += " %s" % filename
        pass
    return result

# This is one of the most complicated functions of the code. It groups
# source files in a package together, so that an IDE can show them nicely.
def getFileGroups( directory ):
    # Some helper variables:
    groups = ""
    currDir = ""
    groupOpen = False
    # Walk through the directory tree:
    for root, dirs, files in os.walk( directory, topdown = True ):
        # Construct a name for the new subgroup:
        group = root[ len( directory ) + 1 : ]
        group = group.replace( "/", "\\\\" )
        # Loop over the files:
        for name in files:
            # Check if it's a source file:
            import fnmatch
            if fnmatch.fnmatch( name, "*.h" ) or \
              fnmatch.fnmatch( name, "*.icc" ) or \
              fnmatch.fnmatch( name, "*.cxx" ) or \
              fnmatch.fnmatch( name, "*.xml" ) or \
              fnmatch.fnmatch( name, "Makefile.RootCore" ):
                # Make sure that a group is open:
                if not groupOpen:
                    # A little sanity check:
                    if not len( group ):
                        print( "getFileGroups(): Found some source files in a "
                               "non-sub-directory" )
                        return ""
                    groups += "source_group( %s FILES" % group
                    groupOpen = True
                    pass
                # Add the file to the group:
                groups += " " + os.path.join( root, name )
                pass
            pass
        # Close the group:
        if groupOpen:
            groups += " )\n"
            groupOpen = False
            pass
        pass
    # Return the collected info:
    return groups

# C-style main function for the script
def main():

    # Define some command line options:
    import optparse
    parser = optparse.OptionParser( description = "This script can be used to "
                                    "generate an Xcode project file for the "
                                    "checked-out RootCore packages",
                                    version = "0.1",
                                    usage = "%prog [options]" )
    parser.add_option( "-p", "--project", dest = "project",
                       action = "store", type = "string",
                       help = "Name of the CMake project",
                       default = "RootCore" )

    ( options, unrec ) = parser.parse_args()

    # Complain about unrecognised options:
    if len( unrec ):
        print "ERROR: Didn't recognise option(s): %s" % str( unrec )
        return 1

    # Let the user know what's happening:
    print( "Collecting information about local packages." )
    print( "This could take a moment..." )

    # Ask RootCore for the names of all the packages:
    packages = runCommand( "rc package_list" ).split()

    # Get the work directory:
    workdir = getWorkDir()
    
    # Select which ones are checked out locally:
    localPackages = []
    for package in packages:
        packagePath = runCommand( "rc get_location " + package ).strip()
        if packagePath.find( workdir ) == 0:
            localPackages += [ package ]
            pass
        pass
    print( "\nLocal packages: %s\n" % str( localPackages ) )

    # Start constructing the CMake file:
    cmakeContent  = "cmake_minimum_required( VERSION 2.8.12 )\n\n"

    # Some basic settings:
    cmakeContent += "set( CMAKE_MACOSX_RPATH ON )\n"
    cmakeContent += "set( CMAKE_CXX_FLAGS \"${CMAKE_CXX_FLAGS} " \
      "-Wall -pedantic -Wextra\" )\n\n"

    # Specify the compiler that should be used:
    from distutils.spawn import find_executable
    cmakeContent += "set( CMAKE_C_COMPILER %s )\n" % \
      find_executable( runCommand( "root-config --cc" ),
                       os.environ[ "PATH" ] )
    cmakeContent += "set( CMAKE_CXX_COMPILER %s )\n\n" % \
      find_executable( runCommand( "root-config --cxx" ),
                       os.environ[ "PATH" ] )

    # Set up the environment for the build. Notice that I don't bother
    # setting DYLD_LIBRARY_PATH. That's because all these settings
    # are only needed for linux anyway. On MacOS X we (should) always use the
    # system default compiler...
    cmakeContent += "set( ENV{PATH} %s )\n" % os.environ[ "PATH" ]
    cmakeContent += "set( ENV{LD_LIBRARY_PATH} %s )\n\n" % \
      os.environ[ "LD_LIBRARY_PATH" ]

    # Start setting up the actual project:
    cmakeContent += "project( %s )\n\n" % options.project
      
    # Loop over the local packages:
    for package in localPackages:

        # A little message to the user:
        print( "Generating description for package: %s" % package )

        # Get the location of the package:
        location = runCommand( "rc get_location " + package )
        # Get the compilation flags for the package:
        cflags = runCommand( "rc get_cxxflags " + package )
        # Get the linker flags for the package:
        ldflags = runCommand( "rc get_ldflags " + package )
        # Get the include directories for this package:
        includes = [ location ]
        includes += getFlags( cflags, "-I" )
        includes += [ runCommand( "root-config --incdir" ) ]
        # Get the pre-compiler macros:
        definitions = getFlags( cflags, "-D" )
        # Get the library directories for this package:
        libdirs  = getFlags( ldflags, "-L" )
        libdirs += [ runCommand( "root-config --libdir" ) ]
        # Get the libraries that this package depends on:
        libraries  = getFlags( ldflags, "-l" )
        libraries += getFlags( runCommand( "root-config --libs" ), "-l" )

        # Overall options coming from this package:
        cmakeContent += "\n\n# Overall options for package %s\n" % package
        cmakeContent += "link_directories( %s )\n" % " ".join( libdirs )

        # Set up the library build for the package:
        if libraries.count( package ):
            cmakeContent += "\n\n# Library built from package %s\n" % package
            cmakeContent += "add_library( %s STATIC %s %s %s %s %s %s %s %s )\n" % \
                ( package, getFiles( os.path.join( location, "Root" ), "*.cxx" ),
                  getFiles( os.path.join( location, "Root" ), "*.h" ),
                  getFiles( os.path.join( location, "Root" ), "*.icc" ),
                  getFiles( os.path.join( location, package ), "*.h" ),
                  getFiles( os.path.join( location, package ), "*.icc" ),
                  getFiles( os.path.join( location, package ), "*.xml" ),
                  os.path.join( os.path.join( location, "cmt" ),
                                "Makefile.RootCore" ),
                  getFiles( location, "ChangeLog" ) )
            cmakeContent += "target_include_directories( %s PUBLIC %s )\n" % \
                ( package, " ".join( includes ) )
            cmakeContent += "target_compile_definitions( %s PUBLIC %s )\n" % \
                ( package, " ".join( definitions ) )
            cmakeContent += "target_compile_options( %s PUBLIC %s %s )\n" % \
                ( package, cflags, runCommand( "root-config --cflags" ) )
            externalLibs = list( libraries )
            externalLibs.remove( package )
            cmakeContent += "target_link_libraries( %s PUBLIC %s )\n" % \
                ( package, " ".join( externalLibs ) )
            pass

        # Declare any possible executables that the package has:
        applications = glob.glob( os.path.join( os.path.join( location,
                                                              "util" ),
                                                "*.cxx" ) )
        applications += glob.glob( os.path.join( os.path.join( location,
                                                                "test" ),
                                                 "*.cxx" ) )
        for app in applications:
            # The name for the executable:
            name = os.path.splitext( os.path.basename( app ) )[ 0 ]
            cmakeContent += "\n\n# Executable %s built from package %s\n" % \
              ( name, package )
            cmakeContent += "add_executable( %s %s )\n" % ( name, app )
            cmakeContent += "target_include_directories( %s PUBLIC %s )\n" % \
                ( name, " ".join( includes ) )
            cmakeContent += "target_compile_definitions( %s PUBLIC %s )\n" % \
                ( name, " ".join( definitions ) )
            cmakeContent += "target_compile_options( %s PUBLIC %s %s )\n" % \
                ( name, cflags, runCommand( "root-config --cflags" ) )
            cmakeContent += "target_link_libraries( %s PRIVATE %s )\n" % \
              ( name, " ".join( libraries ) )
            pass

        # Group the files of this package nicely in the IDE:
        cmakeContent += "\n\n# Source file grouping for package %s\n" % package
        cmakeContent += getFileGroups( location )
        
        pass

    cmakeFileName = "CMakeLists.txt"
    print( "\nWriting cmake file: %s" % cmakeFileName )
    cmakeFile = open( cmakeFileName, "w" )
    cmakeFile.write( cmakeContent )
    cmakeFile.close()

    # Return gracefully:
    return 0

# Execute the C-style main function:
if __name__ == "__main__":
    import sys
    sys.exit( main() )
