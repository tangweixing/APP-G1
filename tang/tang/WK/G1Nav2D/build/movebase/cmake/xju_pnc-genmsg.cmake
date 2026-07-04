# generated from genmsg/cmake/pkg-genmsg.cmake.em

message(STATUS "xju_pnc: 0 messages, 1 services")

set(MSG_I_FLAGS "")

# Find all generators
find_package(gencpp REQUIRED)
find_package(geneus REQUIRED)
find_package(genlisp REQUIRED)
find_package(gennodejs REQUIRED)
find_package(genpy REQUIRED)

add_custom_target(xju_pnc_generate_messages ALL)

# verify that message/service dependencies have not changed since configure



get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/movebase/srv/xju_task.srv" NAME_WE)
add_custom_target(_xju_pnc_generate_messages_check_deps_${_filename}
  COMMAND ${CATKIN_ENV} ${PYTHON_EXECUTABLE} ${GENMSG_CHECK_DEPS_SCRIPT} "xju_pnc" "/home/unitree/tang/WK/G1Nav2D/src/movebase/srv/xju_task.srv" ""
)

#
#  langs = gencpp;geneus;genlisp;gennodejs;genpy
#

### Section generating for lang: gencpp
### Generating Messages

### Generating Services
_generate_srv_cpp(xju_pnc
  "/home/unitree/tang/WK/G1Nav2D/src/movebase/srv/xju_task.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${gencpp_INSTALL_DIR}/xju_pnc
)

### Generating Module File
_generate_module_cpp(xju_pnc
  ${CATKIN_DEVEL_PREFIX}/${gencpp_INSTALL_DIR}/xju_pnc
  "${ALL_GEN_OUTPUT_FILES_cpp}"
)

add_custom_target(xju_pnc_generate_messages_cpp
  DEPENDS ${ALL_GEN_OUTPUT_FILES_cpp}
)
add_dependencies(xju_pnc_generate_messages xju_pnc_generate_messages_cpp)

# add dependencies to all check dependencies targets
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/movebase/srv/xju_task.srv" NAME_WE)
add_dependencies(xju_pnc_generate_messages_cpp _xju_pnc_generate_messages_check_deps_${_filename})

# target for backward compatibility
add_custom_target(xju_pnc_gencpp)
add_dependencies(xju_pnc_gencpp xju_pnc_generate_messages_cpp)

# register target for catkin_package(EXPORTED_TARGETS)
list(APPEND ${PROJECT_NAME}_EXPORTED_TARGETS xju_pnc_generate_messages_cpp)

### Section generating for lang: geneus
### Generating Messages

### Generating Services
_generate_srv_eus(xju_pnc
  "/home/unitree/tang/WK/G1Nav2D/src/movebase/srv/xju_task.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${geneus_INSTALL_DIR}/xju_pnc
)

### Generating Module File
_generate_module_eus(xju_pnc
  ${CATKIN_DEVEL_PREFIX}/${geneus_INSTALL_DIR}/xju_pnc
  "${ALL_GEN_OUTPUT_FILES_eus}"
)

add_custom_target(xju_pnc_generate_messages_eus
  DEPENDS ${ALL_GEN_OUTPUT_FILES_eus}
)
add_dependencies(xju_pnc_generate_messages xju_pnc_generate_messages_eus)

# add dependencies to all check dependencies targets
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/movebase/srv/xju_task.srv" NAME_WE)
add_dependencies(xju_pnc_generate_messages_eus _xju_pnc_generate_messages_check_deps_${_filename})

# target for backward compatibility
add_custom_target(xju_pnc_geneus)
add_dependencies(xju_pnc_geneus xju_pnc_generate_messages_eus)

# register target for catkin_package(EXPORTED_TARGETS)
list(APPEND ${PROJECT_NAME}_EXPORTED_TARGETS xju_pnc_generate_messages_eus)

### Section generating for lang: genlisp
### Generating Messages

### Generating Services
_generate_srv_lisp(xju_pnc
  "/home/unitree/tang/WK/G1Nav2D/src/movebase/srv/xju_task.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${genlisp_INSTALL_DIR}/xju_pnc
)

### Generating Module File
_generate_module_lisp(xju_pnc
  ${CATKIN_DEVEL_PREFIX}/${genlisp_INSTALL_DIR}/xju_pnc
  "${ALL_GEN_OUTPUT_FILES_lisp}"
)

add_custom_target(xju_pnc_generate_messages_lisp
  DEPENDS ${ALL_GEN_OUTPUT_FILES_lisp}
)
add_dependencies(xju_pnc_generate_messages xju_pnc_generate_messages_lisp)

# add dependencies to all check dependencies targets
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/movebase/srv/xju_task.srv" NAME_WE)
add_dependencies(xju_pnc_generate_messages_lisp _xju_pnc_generate_messages_check_deps_${_filename})

# target for backward compatibility
add_custom_target(xju_pnc_genlisp)
add_dependencies(xju_pnc_genlisp xju_pnc_generate_messages_lisp)

# register target for catkin_package(EXPORTED_TARGETS)
list(APPEND ${PROJECT_NAME}_EXPORTED_TARGETS xju_pnc_generate_messages_lisp)

### Section generating for lang: gennodejs
### Generating Messages

### Generating Services
_generate_srv_nodejs(xju_pnc
  "/home/unitree/tang/WK/G1Nav2D/src/movebase/srv/xju_task.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${gennodejs_INSTALL_DIR}/xju_pnc
)

### Generating Module File
_generate_module_nodejs(xju_pnc
  ${CATKIN_DEVEL_PREFIX}/${gennodejs_INSTALL_DIR}/xju_pnc
  "${ALL_GEN_OUTPUT_FILES_nodejs}"
)

add_custom_target(xju_pnc_generate_messages_nodejs
  DEPENDS ${ALL_GEN_OUTPUT_FILES_nodejs}
)
add_dependencies(xju_pnc_generate_messages xju_pnc_generate_messages_nodejs)

# add dependencies to all check dependencies targets
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/movebase/srv/xju_task.srv" NAME_WE)
add_dependencies(xju_pnc_generate_messages_nodejs _xju_pnc_generate_messages_check_deps_${_filename})

# target for backward compatibility
add_custom_target(xju_pnc_gennodejs)
add_dependencies(xju_pnc_gennodejs xju_pnc_generate_messages_nodejs)

# register target for catkin_package(EXPORTED_TARGETS)
list(APPEND ${PROJECT_NAME}_EXPORTED_TARGETS xju_pnc_generate_messages_nodejs)

### Section generating for lang: genpy
### Generating Messages

### Generating Services
_generate_srv_py(xju_pnc
  "/home/unitree/tang/WK/G1Nav2D/src/movebase/srv/xju_task.srv"
  "${MSG_I_FLAGS}"
  ""
  ${CATKIN_DEVEL_PREFIX}/${genpy_INSTALL_DIR}/xju_pnc
)

### Generating Module File
_generate_module_py(xju_pnc
  ${CATKIN_DEVEL_PREFIX}/${genpy_INSTALL_DIR}/xju_pnc
  "${ALL_GEN_OUTPUT_FILES_py}"
)

add_custom_target(xju_pnc_generate_messages_py
  DEPENDS ${ALL_GEN_OUTPUT_FILES_py}
)
add_dependencies(xju_pnc_generate_messages xju_pnc_generate_messages_py)

# add dependencies to all check dependencies targets
get_filename_component(_filename "/home/unitree/tang/WK/G1Nav2D/src/movebase/srv/xju_task.srv" NAME_WE)
add_dependencies(xju_pnc_generate_messages_py _xju_pnc_generate_messages_check_deps_${_filename})

# target for backward compatibility
add_custom_target(xju_pnc_genpy)
add_dependencies(xju_pnc_genpy xju_pnc_generate_messages_py)

# register target for catkin_package(EXPORTED_TARGETS)
list(APPEND ${PROJECT_NAME}_EXPORTED_TARGETS xju_pnc_generate_messages_py)



if(gencpp_INSTALL_DIR AND EXISTS ${CATKIN_DEVEL_PREFIX}/${gencpp_INSTALL_DIR}/xju_pnc)
  # install generated code
  install(
    DIRECTORY ${CATKIN_DEVEL_PREFIX}/${gencpp_INSTALL_DIR}/xju_pnc
    DESTINATION ${gencpp_INSTALL_DIR}
  )
endif()

if(geneus_INSTALL_DIR AND EXISTS ${CATKIN_DEVEL_PREFIX}/${geneus_INSTALL_DIR}/xju_pnc)
  # install generated code
  install(
    DIRECTORY ${CATKIN_DEVEL_PREFIX}/${geneus_INSTALL_DIR}/xju_pnc
    DESTINATION ${geneus_INSTALL_DIR}
  )
endif()

if(genlisp_INSTALL_DIR AND EXISTS ${CATKIN_DEVEL_PREFIX}/${genlisp_INSTALL_DIR}/xju_pnc)
  # install generated code
  install(
    DIRECTORY ${CATKIN_DEVEL_PREFIX}/${genlisp_INSTALL_DIR}/xju_pnc
    DESTINATION ${genlisp_INSTALL_DIR}
  )
endif()

if(gennodejs_INSTALL_DIR AND EXISTS ${CATKIN_DEVEL_PREFIX}/${gennodejs_INSTALL_DIR}/xju_pnc)
  # install generated code
  install(
    DIRECTORY ${CATKIN_DEVEL_PREFIX}/${gennodejs_INSTALL_DIR}/xju_pnc
    DESTINATION ${gennodejs_INSTALL_DIR}
  )
endif()

if(genpy_INSTALL_DIR AND EXISTS ${CATKIN_DEVEL_PREFIX}/${genpy_INSTALL_DIR}/xju_pnc)
  install(CODE "execute_process(COMMAND \"/bin/python3\" -m compileall \"${CATKIN_DEVEL_PREFIX}/${genpy_INSTALL_DIR}/xju_pnc\")")
  # install generated code
  install(
    DIRECTORY ${CATKIN_DEVEL_PREFIX}/${genpy_INSTALL_DIR}/xju_pnc
    DESTINATION ${genpy_INSTALL_DIR}
  )
endif()
