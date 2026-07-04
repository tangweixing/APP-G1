cmake_minimum_required(VERSION 2.8.3)
project(xju_pnc)

add_compile_options(-std=c++17)

find_package(catkin REQUIRED COMPONENTS
        actionlib
        actionlib_msgs
        costmap_2d
        
        gazebo_msgs
        geometry_msgs
        message_generation
        
        nav_msgs
        roscpp
        roslaunch
        sensor_msgs
        tf2
        tf2_ros
        )

add_service_files(
        DIRECTORY srv
        FILES
        xju_task.srv
)

generate_messages()

catkin_package(CATKIN_DEPENDS
        actionlib_msgs
        costmap_2d
        
        
        geometry_msgs
        message_runtime
        
        nav_msgs
        roscpp
        sensor_msgs
        tf2
        tf2_ros
        )

include_directories(include/${PROJECT_NAME} ${catkin_INCLUDE_DIRS})
add_executable(costmap_clear src/costmap_clear.cpp)
target_link_libraries(costmap_clear
  ${catkin_LIBRARIES} ${PCL_LIBRARIES}
)

