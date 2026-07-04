# generated from genmsg/cmake/pkg-genmsg.cmake.em

message(STATUS "fastlio: 0 messages, 6 services")

set(MSG_I_FLAGS "-Istd_msgs:/opt/ros/noetic/share/std_msgs/cmake/../msg")

# Find all generators
find_package(gencpp REQUIRED)
find_package(geneus REQUIRED)
find_package(genlisp REQUIRED)
find_package(gennodejs REQUIRED)
find_package(genpy REQUIRED)

add_custom_target(fastlio_generate_messages ALL)

# verify that message/service dependencies have not changed since configure



get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamReLoc.srv" NAME_WE)
add_custom_target(_fastlio_generate_messages_check_deps_${_filename}
  COMMAND ${CATKIN_ENV} ${PYTHON_EXECUTABLE} ${GENMSG_CHECK_DEPS_SCRIPT} "fastlio" "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamReLoc.srv" ""
)

get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SaveMap.srv" NAME_WE)
add_custom_target(_fastlio_generate_messages_check_deps_${_filename}
  COMMAND ${CATKIN_ENV} ${PYTHON_EXECUTABLE} ${GENMSG_CHECK_DEPS_SCRIPT} "fastlio" "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SaveMap.srv" ""
)

get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/MapConvert.srv" NAME_WE)
add_custom_target(_fastlio_generate_messages_check_deps_${_filename}
  COMMAND ${CATKIN_ENV} ${PYTHON_EXECUTABLE} ${GENMSG_CHECK_DEPS_SCRIPT} "fastlio" "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/MapConvert.srv" ""
)

get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamHold.srv" NAME_WE)
add_custom_target(_fastlio_generate_messages_check_deps_${_filename}
  COMMAND ${CATKIN_ENV} ${PYTHON_EXECUTABLE} ${GENMSG_CHECK_DEPS_SCRIPT} "fastlio" "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamHold.srv" ""
)

get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamStart.srv" NAME_WE)
add_custom_target(_fastlio_generate_messages_check_deps_${_filename}
  COMMAND ${CATKIN_ENV} ${PYTHON_EXECUTABLE} ${GENMSG_CHECK_DEPS_SCRIPT} "fastlio" "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamStart.srv" ""
)

get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamRelocCheck.srv" NAME_WE)
add_custom_target(_fastlio_generate_messages_check_deps_${_filename}
  COMMAND ${CATKIN_ENV} ${PYTHON_EXECUTABLE} ${GENMSG_CHECK_DEPS_SCRIPT} "fastlio" "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamRelocCheck.srv" ""
)

#
#  langs = gencpp;geneus;genlisp;gennodejs;genpy
#

### Section generating for lang: gencpp
### Generating Messages

### Generating Services
_generate_srv_cpp(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamReLoc.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${gencpp_INSTALL_DIR}/fastlio
)
_generate_srv_cpp(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SaveMap.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${gencpp_INSTALL_DIR}/fastlio
)
_generate_srv_cpp(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/MapConvert.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${gencpp_INSTALL_DIR}/fastlio
)
_generate_srv_cpp(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamHold.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${gencpp_INSTALL_DIR}/fastlio
)
_generate_srv_cpp(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamStart.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${gencpp_INSTALL_DIR}/fastlio
)
_generate_srv_cpp(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamRelocCheck.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${gencpp_INSTALL_DIR}/fastlio
)

### Generating Module File
_generate_module_cpp(fastlio
  ${CATKIN_DEVEL_PREFIX}/${gencpp_INSTALL_DIR}/fastlio
  "${ALL_GEN_OUTPUT_FILES_cpp}"
)

add_custom_target(fastlio_generate_messages_cpp
  DEPENDS ${ALL_GEN_OUTPUT_FILES_cpp}
)
add_dependencies(fastlio_generate_messages fastlio_generate_messages_cpp)

# add dependencies to all check dependencies targets
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamReLoc.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_cpp _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SaveMap.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_cpp _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/MapConvert.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_cpp _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamHold.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_cpp _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamStart.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_cpp _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamRelocCheck.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_cpp _fastlio_generate_messages_check_deps_${_filename})

# target for backward compatibility
add_custom_target(fastlio_gencpp)
add_dependencies(fastlio_gencpp fastlio_generate_messages_cpp)

# register target for catkin_package(EXPORTED_TARGETS)
list(APPEND ${PROJECT_NAME}_EXPORTED_TARGETS fastlio_generate_messages_cpp)

### Section generating for lang: geneus
### Generating Messages

### Generating Services
_generate_srv_eus(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamReLoc.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${geneus_INSTALL_DIR}/fastlio
)
_generate_srv_eus(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SaveMap.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${geneus_INSTALL_DIR}/fastlio
)
_generate_srv_eus(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/MapConvert.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${geneus_INSTALL_DIR}/fastlio
)
_generate_srv_eus(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamHold.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${geneus_INSTALL_DIR}/fastlio
)
_generate_srv_eus(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamStart.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${geneus_INSTALL_DIR}/fastlio
)
_generate_srv_eus(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamRelocCheck.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${geneus_INSTALL_DIR}/fastlio
)

### Generating Module File
_generate_module_eus(fastlio
  ${CATKIN_DEVEL_PREFIX}/${geneus_INSTALL_DIR}/fastlio
  "${ALL_GEN_OUTPUT_FILES_eus}"
)

add_custom_target(fastlio_generate_messages_eus
  DEPENDS ${ALL_GEN_OUTPUT_FILES_eus}
)
add_dependencies(fastlio_generate_messages fastlio_generate_messages_eus)

# add dependencies to all check dependencies targets
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamReLoc.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_eus _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SaveMap.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_eus _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/MapConvert.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_eus _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamHold.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_eus _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamStart.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_eus _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamRelocCheck.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_eus _fastlio_generate_messages_check_deps_${_filename})

# target for backward compatibility
add_custom_target(fastlio_geneus)
add_dependencies(fastlio_geneus fastlio_generate_messages_eus)

# register target for catkin_package(EXPORTED_TARGETS)
list(APPEND ${PROJECT_NAME}_EXPORTED_TARGETS fastlio_generate_messages_eus)

### Section generating for lang: genlisp
### Generating Messages

### Generating Services
_generate_srv_lisp(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamReLoc.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${genlisp_INSTALL_DIR}/fastlio
)
_generate_srv_lisp(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SaveMap.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${genlisp_INSTALL_DIR}/fastlio
)
_generate_srv_lisp(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/MapConvert.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${genlisp_INSTALL_DIR}/fastlio
)
_generate_srv_lisp(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamHold.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${genlisp_INSTALL_DIR}/fastlio
)
_generate_srv_lisp(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamStart.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${genlisp_INSTALL_DIR}/fastlio
)
_generate_srv_lisp(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamRelocCheck.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${genlisp_INSTALL_DIR}/fastlio
)

### Generating Module File
_generate_module_lisp(fastlio
  ${CATKIN_DEVEL_PREFIX}/${genlisp_INSTALL_DIR}/fastlio
  "${ALL_GEN_OUTPUT_FILES_lisp}"
)

add_custom_target(fastlio_generate_messages_lisp
  DEPENDS ${ALL_GEN_OUTPUT_FILES_lisp}
)
add_dependencies(fastlio_generate_messages fastlio_generate_messages_lisp)

# add dependencies to all check dependencies targets
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamReLoc.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_lisp _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SaveMap.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_lisp _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/MapConvert.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_lisp _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamHold.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_lisp _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamStart.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_lisp _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamRelocCheck.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_lisp _fastlio_generate_messages_check_deps_${_filename})

# target for backward compatibility
add_custom_target(fastlio_genlisp)
add_dependencies(fastlio_genlisp fastlio_generate_messages_lisp)

# register target for catkin_package(EXPORTED_TARGETS)
list(APPEND ${PROJECT_NAME}_EXPORTED_TARGETS fastlio_generate_messages_lisp)

### Section generating for lang: gennodejs
### Generating Messages

### Generating Services
_generate_srv_nodejs(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamReLoc.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${gennodejs_INSTALL_DIR}/fastlio
)
_generate_srv_nodejs(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SaveMap.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${gennodejs_INSTALL_DIR}/fastlio
)
_generate_srv_nodejs(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/MapConvert.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${gennodejs_INSTALL_DIR}/fastlio
)
_generate_srv_nodejs(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamHold.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${gennodejs_INSTALL_DIR}/fastlio
)
_generate_srv_nodejs(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamStart.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${gennodejs_INSTALL_DIR}/fastlio
)
_generate_srv_nodejs(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamRelocCheck.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${gennodejs_INSTALL_DIR}/fastlio
)

### Generating Module File
_generate_module_nodejs(fastlio
  ${CATKIN_DEVEL_PREFIX}/${gennodejs_INSTALL_DIR}/fastlio
  "${ALL_GEN_OUTPUT_FILES_nodejs}"
)

add_custom_target(fastlio_generate_messages_nodejs
  DEPENDS ${ALL_GEN_OUTPUT_FILES_nodejs}
)
add_dependencies(fastlio_generate_messages fastlio_generate_messages_nodejs)

# add dependencies to all check dependencies targets
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamReLoc.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_nodejs _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SaveMap.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_nodejs _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/MapConvert.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_nodejs _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamHold.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_nodejs _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamStart.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_nodejs _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamRelocCheck.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_nodejs _fastlio_generate_messages_check_deps_${_filename})

# target for backward compatibility
add_custom_target(fastlio_gennodejs)
add_dependencies(fastlio_gennodejs fastlio_generate_messages_nodejs)

# register target for catkin_package(EXPORTED_TARGETS)
list(APPEND ${PROJECT_NAME}_EXPORTED_TARGETS fastlio_generate_messages_nodejs)

### Section generating for lang: genpy
### Generating Messages

### Generating Services
_generate_srv_py(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamReLoc.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${genpy_INSTALL_DIR}/fastlio
)
_generate_srv_py(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SaveMap.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${genpy_INSTALL_DIR}/fastlio
)
_generate_srv_py(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/MapConvert.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${genpy_INSTALL_DIR}/fastlio
)
_generate_srv_py(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamHold.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${genpy_INSTALL_DIR}/fastlio
)
_generate_srv_py(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamStart.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${genpy_INSTALL_DIR}/fastlio
)
_generate_srv_py(fastlio
  "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamRelocCheck.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${genpy_INSTALL_DIR}/fastlio
)

### Generating Module File
_generate_module_py(fastlio
  ${CATKIN_DEVEL_PREFIX}/${genpy_INSTALL_DIR}/fastlio
  "${ALL_GEN_OUTPUT_FILES_py}"
)

add_custom_target(fastlio_generate_messages_py
  DEPENDS ${ALL_GEN_OUTPUT_FILES_py}
)
add_dependencies(fastlio_generate_messages fastlio_generate_messages_py)

# add dependencies to all check dependencies targets
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamReLoc.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_py _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SaveMap.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_py _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/MapConvert.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_py _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamHold.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_py _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamStart.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_py _fastlio_generate_messages_check_deps_${_filename})
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/fastlio2/srv/SlamRelocCheck.srv" NAME_WE)
add_dependencies(fastlio_generate_messages_py _fastlio_generate_messages_check_deps_${_filename})

# target for backward compatibility
add_custom_target(fastlio_genpy)
add_dependencies(fastlio_genpy fastlio_generate_messages_py)

# register target for catkin_package(EXPORTED_TARGETS)
list(APPEND ${PROJECT_NAME}_EXPORTED_TARGETS fastlio_generate_messages_py)



if(gencpp_INSTALL_DIR AND EXISTS ${CATKIN_DEVEL_PREFIX}/${gencpp_INSTALL_DIR}/fastlio)
  # install generated code
  install(
    DIRECTORY ${CATKIN_DEVEL_PREFIX}/${gencpp_INSTALL_DIR}/fastlio
    DESTINATION ${gencpp_INSTALL_DIR}
  )
endif()
if(TARGET std_msgs_generate_messages_cpp)
  add_dependencies(fastlio_generate_messages_cpp std_msgs_generate_messages_cpp)
endif()

if(geneus_INSTALL_DIR AND EXISTS ${CATKIN_DEVEL_PREFIX}/${geneus_INSTALL_DIR}/fastlio)
  # install generated code
  install(
    DIRECTORY ${CATKIN_DEVEL_PREFIX}/${geneus_INSTALL_DIR}/fastlio
    DESTINATION ${geneus_INSTALL_DIR}
  )
endif()
if(TARGET std_msgs_generate_messages_eus)
  add_dependencies(fastlio_generate_messages_eus std_msgs_generate_messages_eus)
endif()

if(genlisp_INSTALL_DIR AND EXISTS ${CATKIN_DEVEL_PREFIX}/${genlisp_INSTALL_DIR}/fastlio)
  # install generated code
  install(
    DIRECTORY ${CATKIN_DEVEL_PREFIX}/${genlisp_INSTALL_DIR}/fastlio
    DESTINATION ${genlisp_INSTALL_DIR}
  )
endif()
if(TARGET std_msgs_generate_messages_lisp)
  add_dependencies(fastlio_generate_messages_lisp std_msgs_generate_messages_lisp)
endif()

if(gennodejs_INSTALL_DIR AND EXISTS ${CATKIN_DEVEL_PREFIX}/${gennodejs_INSTALL_DIR}/fastlio)
  # install generated code
  install(
    DIRECTORY ${CATKIN_DEVEL_PREFIX}/${gennodejs_INSTALL_DIR}/fastlio
    DESTINATION ${gennodejs_INSTALL_DIR}
  )
endif()
if(TARGET std_msgs_generate_messages_nodejs)
  add_dependencies(fastlio_generate_messages_nodejs std_msgs_generate_messages_nodejs)
endif()

if(genpy_INSTALL_DIR AND EXISTS ${CATKIN_DEVEL_PREFIX}/${genpy_INSTALL_DIR}/fastlio)
  install(CODE "execute_process(COMMAND \"/bin/python3\" -m compileall \"${CATKIN_DEVEL_PREFIX}/${genpy_INSTALL_DIR}/fastlio\")")
  # install generated code
  install(
    DIRECTORY ${CATKIN_DEVEL_PREFIX}/${genpy_INSTALL_DIR}/fastlio
    DESTINATION ${genpy_INSTALL_DIR}
  )
endif()
if(TARGET std_msgs_generate_messages_py)
  add_dependencies(fastlio_generate_messages_py std_msgs_generate_messages_py)
endif()
