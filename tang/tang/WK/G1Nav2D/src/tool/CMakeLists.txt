cmake_minimum_required(VERSION 3.0.2)
project(tool)


ADD_COMPILE_OPTIONS(-std=c++14 )
ADD_COMPILE_OPTIONS(-std=c++14 )
set( CMAKE_CXX_FLAGS "-std=c++14 -O3" )

set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fexceptions" )
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++14 -pthread -std=c++0x -std=c++14 -fexceptions")

message("Current CPU archtecture: ${CMAKE_SYSTEM_PROCESSOR}")
if(CMAKE_SYSTEM_PROCESSOR MATCHES "(x86)|(X86)|(amd64)|(AMD64)" )
  include(ProcessorCount)
  ProcessorCount(N)
  message("Processer number:  ${N}")
  if(N GREATER 4)
    add_definitions(-DMP_EN)
    add_definitions(-DMP_PROC_NUM=3)
    message("core for MP: 3")
  elseif(N GREATER 3)
    add_definitions(-DMP_EN)
    add_definitions(-DMP_PROC_NUM=2)
    message("core for MP: 2")
  else()
    add_definitions(-DMP_PROC_NUM=1)
  endif()
else()
  add_definitions(-DMP_PROC_NUM=1)
endif()

find_package(OpenMP QUIET)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS}   ${OpenMP_C_FLAGS}")


find_package(catkin REQUIRED COMPONENTS
  tf2
  tf2_ros
  roscpp
  std_msgs
  nav_msgs
  sensor_msgs
  geometry_msgs
  pcl_ros
  livox_ros_driver2
  message_generation
  eigen_conversions
)

find_package(PCL REQUIRED)
find_package(Eigen3 REQUIRED)

# find_package( GTSAMCMakeTools )
find_package(GTSAM REQUIRED)






generate_messages(
  DEPENDENCIES
  std_msgs
)


catkin_package(
#  INCLUDE_DIRS include
#  LIBRARIES fastlio
#  CATKIN_DEPENDS roscpp std_msgs
#  DEPENDS system_lib
)


include_directories(
  include
  ${catkin_INCLUDE_DIRS}
  ${EIGEN3_INCLUDE_DIR}
  ${PCL_INCLUDE_DIRS}
)


add_executable(path2waypoint src/path2waypoint.cpp)

target_link_libraries(path2waypoint
  ${catkin_LIBRARIES} ${PCL_LIBRARIES}
)

add_executable(body2map_pointcloud src/body2map_pointcloud.cpp)

target_link_libraries(body2map_pointcloud
  ${catkin_LIBRARIES} ${PCL_LIBRARIES}
)

add_executable(body2any_pointcloud src/body2any_pointcloud.cpp)

target_link_libraries(body2any_pointcloud
  ${catkin_LIBRARIES} ${PCL_LIBRARIES}
)

add_executable(livox2velodyne src/livox2velodyne.cpp )
target_link_libraries(livox2velodyne ${catkin_LIBRARIES} ${PCL_LIBRARIES} ${PYTHON_LIBRARIES})
target_include_directories(livox2velodyne PRIVATE ${PYTHON_INCLUDE_DIRS})

add_executable(downsample_pointcloud src/downsample_pointcloud.cpp)

target_link_libraries(downsample_pointcloud
  ${catkin_LIBRARIES} ${PCL_LIBRARIES}
)

add_executable(local2map_odom src/local2map_odom.cpp)
target_link_libraries(local2map_odom ${catkin_LIBRARIES})

add_executable(robot_around_pointcloud src/robot_around_pointcloud.cpp)
target_link_libraries(robot_around_pointcloud
  ${catkin_LIBRARIES} ${PCL_LIBRARIES}
)

catkin_install_python(PROGRAMS
scripts/record_teaching_path.py
scripts/play_teaching_path.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)