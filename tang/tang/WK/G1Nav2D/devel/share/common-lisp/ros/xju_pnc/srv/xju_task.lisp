; Auto-generated. Do not edit!


(cl:in-package xju_pnc-srv)


;//! \htmlinclude xju_task-request.msg.html

(cl:defclass <xju_task-request> (roslisp-msg-protocol:ros-message)
  ((type
    :reader type
    :initarg :type
    :type cl:fixnum
    :initform 0)
   (command
    :reader command
    :initarg :command
    :type cl:fixnum
    :initform 0)
   (dir
    :reader dir
    :initarg :dir
    :type cl:string
    :initform "")
   (path_name
    :reader path_name
    :initarg :path_name
    :type cl:string
    :initform "")
   (map
    :reader map
    :initarg :map
    :type cl:string
    :initform ""))
)

(cl:defclass xju_task-request (<xju_task-request>)
  ())

(cl:defmethod cl:initialize-instance :after ((m <xju_task-request>) cl:&rest args)
  (cl:declare (cl:ignorable args))
  (cl:unless (cl:typep m 'xju_task-request)
    (roslisp-msg-protocol:msg-deprecation-warning "using old message class name xju_pnc-srv:<xju_task-request> is deprecated: use xju_pnc-srv:xju_task-request instead.")))

(cl:ensure-generic-function 'type-val :lambda-list '(m))
(cl:defmethod type-val ((m <xju_task-request>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader xju_pnc-srv:type-val is deprecated.  Use xju_pnc-srv:type instead.")
  (type m))

(cl:ensure-generic-function 'command-val :lambda-list '(m))
(cl:defmethod command-val ((m <xju_task-request>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader xju_pnc-srv:command-val is deprecated.  Use xju_pnc-srv:command instead.")
  (command m))

(cl:ensure-generic-function 'dir-val :lambda-list '(m))
(cl:defmethod dir-val ((m <xju_task-request>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader xju_pnc-srv:dir-val is deprecated.  Use xju_pnc-srv:dir instead.")
  (dir m))

(cl:ensure-generic-function 'path_name-val :lambda-list '(m))
(cl:defmethod path_name-val ((m <xju_task-request>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader xju_pnc-srv:path_name-val is deprecated.  Use xju_pnc-srv:path_name instead.")
  (path_name m))

(cl:ensure-generic-function 'map-val :lambda-list '(m))
(cl:defmethod map-val ((m <xju_task-request>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader xju_pnc-srv:map-val is deprecated.  Use xju_pnc-srv:map instead.")
  (map m))
(cl:defmethod roslisp-msg-protocol:symbol-codes ((msg-type (cl:eql '<xju_task-request>)))
    "Constants for message type '<xju_task-request>"
  '((:EXECUTE . 0)
    (:RECORD . 1)
    (:LOAD_TRAFFIC_ROUTE . 2)
    (:QR_NAV . 3)
    (:START . 0)
    (:PAUSE . 1)
    (:STOP . 2)
    (:KEEP_TEACH . 1)
    (:KEEP_COVER_ZZ . 2)
    (:KEEP_COVER_BS . 3)
    (:DISCARD . 4)
    (:KEEP_TRAFFIC_ROUTE . 5))
)
(cl:defmethod roslisp-msg-protocol:symbol-codes ((msg-type (cl:eql 'xju_task-request)))
    "Constants for message type 'xju_task-request"
  '((:EXECUTE . 0)
    (:RECORD . 1)
    (:LOAD_TRAFFIC_ROUTE . 2)
    (:QR_NAV . 3)
    (:START . 0)
    (:PAUSE . 1)
    (:STOP . 2)
    (:KEEP_TEACH . 1)
    (:KEEP_COVER_ZZ . 2)
    (:KEEP_COVER_BS . 3)
    (:DISCARD . 4)
    (:KEEP_TRAFFIC_ROUTE . 5))
)
(cl:defmethod roslisp-msg-protocol:serialize ((msg <xju_task-request>) ostream)
  "Serializes a message object of type '<xju_task-request>"
  (cl:write-byte (cl:ldb (cl:byte 8 0) (cl:slot-value msg 'type)) ostream)
  (cl:write-byte (cl:ldb (cl:byte 8 0) (cl:slot-value msg 'command)) ostream)
  (cl:let ((__ros_str_len (cl:length (cl:slot-value msg 'dir))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) __ros_str_len) ostream))
  (cl:map cl:nil #'(cl:lambda (c) (cl:write-byte (cl:char-code c) ostream)) (cl:slot-value msg 'dir))
  (cl:let ((__ros_str_len (cl:length (cl:slot-value msg 'path_name))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) __ros_str_len) ostream))
  (cl:map cl:nil #'(cl:lambda (c) (cl:write-byte (cl:char-code c) ostream)) (cl:slot-value msg 'path_name))
  (cl:let ((__ros_str_len (cl:length (cl:slot-value msg 'map))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) __ros_str_len) ostream))
  (cl:map cl:nil #'(cl:lambda (c) (cl:write-byte (cl:char-code c) ostream)) (cl:slot-value msg 'map))
)
(cl:defmethod roslisp-msg-protocol:deserialize ((msg <xju_task-request>) istream)
  "Deserializes a message object of type '<xju_task-request>"
    (cl:setf (cl:ldb (cl:byte 8 0) (cl:slot-value msg 'type)) (cl:read-byte istream))
    (cl:setf (cl:ldb (cl:byte 8 0) (cl:slot-value msg 'command)) (cl:read-byte istream))
    (cl:let ((__ros_str_len 0))
      (cl:setf (cl:ldb (cl:byte 8 0) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:slot-value msg 'dir) (cl:make-string __ros_str_len))
      (cl:dotimes (__ros_str_idx __ros_str_len msg)
        (cl:setf (cl:char (cl:slot-value msg 'dir) __ros_str_idx) (cl:code-char (cl:read-byte istream)))))
    (cl:let ((__ros_str_len 0))
      (cl:setf (cl:ldb (cl:byte 8 0) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:slot-value msg 'path_name) (cl:make-string __ros_str_len))
      (cl:dotimes (__ros_str_idx __ros_str_len msg)
        (cl:setf (cl:char (cl:slot-value msg 'path_name) __ros_str_idx) (cl:code-char (cl:read-byte istream)))))
    (cl:let ((__ros_str_len 0))
      (cl:setf (cl:ldb (cl:byte 8 0) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:slot-value msg 'map) (cl:make-string __ros_str_len))
      (cl:dotimes (__ros_str_idx __ros_str_len msg)
        (cl:setf (cl:char (cl:slot-value msg 'map) __ros_str_idx) (cl:code-char (cl:read-byte istream)))))
  msg
)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql '<xju_task-request>)))
  "Returns string type for a service object of type '<xju_task-request>"
  "xju_pnc/xju_taskRequest")
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'xju_task-request)))
  "Returns string type for a service object of type 'xju_task-request"
  "xju_pnc/xju_taskRequest")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql '<xju_task-request>)))
  "Returns md5sum for a message object of type '<xju_task-request>"
  "aadab28b2111acdfca066c4f4a5419ef")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql 'xju_task-request)))
  "Returns md5sum for a message object of type 'xju_task-request"
  "aadab28b2111acdfca066c4f4a5419ef")
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql '<xju_task-request>)))
  "Returns full string definition for message of type '<xju_task-request>"
  (cl:format cl:nil "uint8 EXECUTE = 0~%uint8 RECORD = 1~%uint8 LOAD_TRAFFIC_ROUTE = 2~%uint8 QR_NAV = 3~%~%uint8 START = 0~%uint8 PAUSE = 1~%uint8 STOP = 2~%~%uint8 KEEP_TEACH = 1~%uint8 KEEP_COVER_ZZ = 2~%uint8 KEEP_COVER_BS = 3~%uint8 DISCARD = 4~%uint8 KEEP_TRAFFIC_ROUTE = 5 # only support two points for now~%~%uint8 type #EXECUTE RECORD LOAD_TRAFFIC_ROUTE QR_NAV~%uint8 command #START PAUSE STOP KEEP_TEACH KEEP_COVER DISCARD KEEP_TRAFFIC_ROUTE~%string dir~%string path_name~%string map~%~%~%"))
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql 'xju_task-request)))
  "Returns full string definition for message of type 'xju_task-request"
  (cl:format cl:nil "uint8 EXECUTE = 0~%uint8 RECORD = 1~%uint8 LOAD_TRAFFIC_ROUTE = 2~%uint8 QR_NAV = 3~%~%uint8 START = 0~%uint8 PAUSE = 1~%uint8 STOP = 2~%~%uint8 KEEP_TEACH = 1~%uint8 KEEP_COVER_ZZ = 2~%uint8 KEEP_COVER_BS = 3~%uint8 DISCARD = 4~%uint8 KEEP_TRAFFIC_ROUTE = 5 # only support two points for now~%~%uint8 type #EXECUTE RECORD LOAD_TRAFFIC_ROUTE QR_NAV~%uint8 command #START PAUSE STOP KEEP_TEACH KEEP_COVER DISCARD KEEP_TRAFFIC_ROUTE~%string dir~%string path_name~%string map~%~%~%"))
(cl:defmethod roslisp-msg-protocol:serialization-length ((msg <xju_task-request>))
  (cl:+ 0
     1
     1
     4 (cl:length (cl:slot-value msg 'dir))
     4 (cl:length (cl:slot-value msg 'path_name))
     4 (cl:length (cl:slot-value msg 'map))
))
(cl:defmethod roslisp-msg-protocol:ros-message-to-list ((msg <xju_task-request>))
  "Converts a ROS message object to a list"
  (cl:list 'xju_task-request
    (cl:cons ':type (type msg))
    (cl:cons ':command (command msg))
    (cl:cons ':dir (dir msg))
    (cl:cons ':path_name (path_name msg))
    (cl:cons ':map (map msg))
))
;//! \htmlinclude xju_task-response.msg.html

(cl:defclass <xju_task-response> (roslisp-msg-protocol:ros-message)
  ((message
    :reader message
    :initarg :message
    :type cl:string
    :initform ""))
)

(cl:defclass xju_task-response (<xju_task-response>)
  ())

(cl:defmethod cl:initialize-instance :after ((m <xju_task-response>) cl:&rest args)
  (cl:declare (cl:ignorable args))
  (cl:unless (cl:typep m 'xju_task-response)
    (roslisp-msg-protocol:msg-deprecation-warning "using old message class name xju_pnc-srv:<xju_task-response> is deprecated: use xju_pnc-srv:xju_task-response instead.")))

(cl:ensure-generic-function 'message-val :lambda-list '(m))
(cl:defmethod message-val ((m <xju_task-response>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader xju_pnc-srv:message-val is deprecated.  Use xju_pnc-srv:message instead.")
  (message m))
(cl:defmethod roslisp-msg-protocol:serialize ((msg <xju_task-response>) ostream)
  "Serializes a message object of type '<xju_task-response>"
  (cl:let ((__ros_str_len (cl:length (cl:slot-value msg 'message))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) __ros_str_len) ostream))
  (cl:map cl:nil #'(cl:lambda (c) (cl:write-byte (cl:char-code c) ostream)) (cl:slot-value msg 'message))
)
(cl:defmethod roslisp-msg-protocol:deserialize ((msg <xju_task-response>) istream)
  "Deserializes a message object of type '<xju_task-response>"
    (cl:let ((__ros_str_len 0))
      (cl:setf (cl:ldb (cl:byte 8 0) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:slot-value msg 'message) (cl:make-string __ros_str_len))
      (cl:dotimes (__ros_str_idx __ros_str_len msg)
        (cl:setf (cl:char (cl:slot-value msg 'message) __ros_str_idx) (cl:code-char (cl:read-byte istream)))))
  msg
)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql '<xju_task-response>)))
  "Returns string type for a service object of type '<xju_task-response>"
  "xju_pnc/xju_taskResponse")
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'xju_task-response)))
  "Returns string type for a service object of type 'xju_task-response"
  "xju_pnc/xju_taskResponse")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql '<xju_task-response>)))
  "Returns md5sum for a message object of type '<xju_task-response>"
  "aadab28b2111acdfca066c4f4a5419ef")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql 'xju_task-response)))
  "Returns md5sum for a message object of type 'xju_task-response"
  "aadab28b2111acdfca066c4f4a5419ef")
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql '<xju_task-response>)))
  "Returns full string definition for message of type '<xju_task-response>"
  (cl:format cl:nil "~%string message~%~%~%~%"))
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql 'xju_task-response)))
  "Returns full string definition for message of type 'xju_task-response"
  (cl:format cl:nil "~%string message~%~%~%~%"))
(cl:defmethod roslisp-msg-protocol:serialization-length ((msg <xju_task-response>))
  (cl:+ 0
     4 (cl:length (cl:slot-value msg 'message))
))
(cl:defmethod roslisp-msg-protocol:ros-message-to-list ((msg <xju_task-response>))
  "Converts a ROS message object to a list"
  (cl:list 'xju_task-response
    (cl:cons ':message (message msg))
))
(cl:defmethod roslisp-msg-protocol:service-request-type ((msg (cl:eql 'xju_task)))
  'xju_task-request)
(cl:defmethod roslisp-msg-protocol:service-response-type ((msg (cl:eql 'xju_task)))
  'xju_task-response)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'xju_task)))
  "Returns string type for a service object of type '<xju_task>"
  "xju_pnc/xju_task")