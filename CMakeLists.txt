cmake_minimum_required(VERSION 2.8)
project(object_recognition_core)

find_package(catkin REQUIRED cmake_modules ecto sensor_msgs)
catkin_package(DEPENDS ecto
               CATKIN_DEPENDS sensor_msgs
               INCLUDE_DIRS include
               LIBRARIES object_recognition_core_db object_recognition_core_common
               CFG_EXTRAS test.cmake
)

#install targets for all things python
catkin_python_setup()

add_subdirectory(python)

add_definitions("-Wno-pragmas -fno-strict-aliasing -Wall -Werror -Wno-deprecated")

find_package(Boost COMPONENTS system filesystem serialization python REQUIRED)
find_package(OpenCV REQUIRED)

include_directories(SYSTEM ${Boost_INCLUDE_DIRS}
                           ${OpenCV_INCLUDE_DIRS}
)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include ${catkin_INCLUDE_DIRS})

add_subdirectory(src)
add_subdirectory(web_ui)

#these setup the lib to be used by others
include(cmake/install.cmake)

# add tests
add_subdirectory(share)
if(CATKIN_ENABLE_TESTING)
  add_subdirectory(test)
endif()

# build docs
add_subdirectory(doc)
catkin_doxygen(object_recognition_core-doxygen ${CMAKE_CURRENT_SOURCE_DIR}/include)

# Use the ecto scripts to build top-level documentation
set(ecto_SPHINX_DIR ${CMAKE_CURRENT_SOURCE_DIR}/doc/source)
ecto_sphinx(${CMAKE_CURRENT_SOURCE_DIR}/doc/source doc)
