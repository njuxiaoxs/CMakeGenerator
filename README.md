copy from https://svnweb.cern.ch/cern/wsvn/atlas-krasznaa/AODUpgrade/CMakeGenerator/trunk/

git clone https://github.com/njuxiaoxs/CMakeGenerator.git

mkdir IDE

cd IDE/

../CMakeGenerator/generateRootCoreCMakeProject.py

/*
This will generate a file called CMakeLists.txt in the IDE/ directory. It's worth creating a dedicated directory for the IDE files, as you will need to re-generate these files every time that you make a big update in your work area. (Check out a new package, introduce a new executable, etc.) If you don't have make installed, you can download it here.
You can now use this CMake project description file to generate a project for the IDE of your choice. On MacOS X you can generate a project for Xcode with:
*/

cmake -G Xcode .

/*
This will create a project file called RootCore.xcodeproj that you can just open from the terminal with open RootCore.xcodeproj/.
*/

