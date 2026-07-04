; Auto-generated. Do not edit!


(cl:in-package fastlio-srv)


;//! \htmlinclude MapConvert-request.msg.html

(cl:defclass <MapConvert-request> (roslisp-msg-protocol:ros-message)
  ((map_path
    :reader map_path
    :initarg :map_path
    :type cl:string
    :initform "")
   (save_path
    :reader save_path
    :initarg :save_path
    :type cl:string
    :initform "")
   (resolution
    :reader resolution
    :initarg :resolution
    :type cl:float
    :initform 0.0))
)

(cl:defclass MapConvert-request (<MapConvert-request>)
  ())

(cl:defmethod cl:initialize-instance :after ((m <MapConvert-request>) cl:&rest args)
  (cl:declare (cl:ignorable args))
  (cl:unless (cl:typep m 'MapConvert-request)
    (roslisp-msg-protocol:msg-deprecation-warning "using old message class name fastlio-srv:<MapConvert-request> is deprecated: use fastlio-srv:MapConvert-request instead.")))

(cl:ensure-generic-function 'map_path-val :lambda-list '(m))
(cl:defmethod map_path-val ((m <MapConvert-request>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader fastlio-srv:map_path-val is deprecated.  Use fastlio-srv:map_path instead.")
  (map_path m))

(cl:ensure-generic-function 'save_path-val :lambda-list '(m))
(cl:defmethod save_path-val ((m <MapConvert-request>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader fastlio-srv:save_path-val is deprecated.  Use fastlio-srv:save_path instead.")
  (save_path m))

(cl:ensure-generic-function 'resolution-val :lambda-list '(m))
(cl:defmethod resolution-val ((m <MapConvert-request>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader fastlio-srv:resolution-val is deprecated.  Use fastlio-srv:resolution instead.")
  (resolution m))
(cl:defmethod roslisp-msg-protocol:serialize ((msg <MapConvert-request>) ostream)
  "Serializes a message object of type '<MapConvert-request>"
  (cl:let ((__ros_str_len (cl:length (cl:slot-value msg 'map_path))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) __ros_str_len) ostream))
  (cl:map cl:nil #'(cl:lambda (c) (cl:write-byte (cl:char-code c) ostream)) (cl:slot-value msg 'map_path))
  (cl:let ((__ros_str_len (cl:length (cl:slot-value msg 'save_path))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) __ros_str_len) ostream))
  (cl:map cl:nil #'(cl:lambda (c) (cl:write-byte (cl:char-code c) ostream)) (cl:slot-value msg 'save_path))
  (cl:let ((bits (roslisp-utils:encode-single-float-bits (cl:slot-value msg 'resolution))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) bits) ostream))
)
(cl:defmethod roslisp-msg-protocol:deserialize ((msg <MapConvert-request>) istream)
  "Deserializes a message object of type '<MapConvert-request>"
    (cl:let ((__ros_str_len 0))
      (cl:setf (cl:ldb (cl:byte 8 0) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:slot-value msg 'map_path) (cl:make-string __ros_str_len))
      (cl:dotimes (__ros_str_idx __ros_str_len msg)
        (cl:setf (cl:char (cl:slot-value msg 'map_path) __ros_str_idx) (cl:code-char (cl:read-byte istream)))))
    (cl:let ((__ros_str_len 0))
      (cl:setf (cl:ldb (cl:byte 8 0) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) __ros_str_len) (cl:read-byte istream))
      (cl:setf (cl:slot-value msg 'save_path) (cl:make-string __ros_str_len))
      (cl:dotimes (__ros_str_idx __ros_str_len msg)
        (cl:setf (cl:char (cl:slot-value msg 'save_path) __ros_str_idx) (cl:code-char (cl:read-byte istream)))))
    (cl:let ((bits 0))
      (cl:setf (cl:ldb (cl:byte 8 0) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) bits) (cl:read-byte istream))
    (cl:setf (cl:slot-value msg 'resolution) (roslisp-utils:decode-single-float-bits bits)))
  msg
)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql '<MapConvert-request>)))
  "Returns string type for a service object of type '<MapConvert-request>"
  "fastlio/MapConvertRequest")
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'MapConvert-request)))
  "Returns string type for a service object of type 'MapConvert-request"
  "fastlio/MapConvertRequest")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql '<MapConvert-request>)))
  "Returns md5sum for a message object of type '<MapConvert-request>"
  "27938b198ec2a6b94cdc450d4db81e6d")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql 'MapConvert-request)))
  "Returns md5sum for a message object of type 'MapConvert-request"
  "27938b198ec2a6b94cdc450d4db81e6d")
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql '<MapConvert-request>)))
  "Returns full string definition for message of type '<MapConvert-request>"
  (cl:format cl:nil "string map_path~%string save_path~%float32 resolution~%~%~%"))
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql 'MapConvert-request)))
  "Returns full string definition for message of type 'MapConvert-request"
  (cl:format cl:nil "string map_path~%string save_path~%float32 resolution~%~%~%"))
(cl:defmethod roslisp-msg-protocol:serialization-length ((msg <MapConvert-request>))
  (cl:+ 0
     4 (cl:length (cl:slot-value msg 'map_path))
     4 (cl:length (cl:slot-value msg 'save_path))
     4
))
(cl:defmethod roslisp-msg-protocol:ros-message-to-list ((msg <MapConvert-request>))
  "Converts a ROS message object to a list"
  (cl:list 'MapConvert-request
    (cl:cons ':map_path (map_path msg))
    (cl:cons ':save_path (save_path msg))
    (cl:cons ':resolution (resolution msg))
))
;//! \htmlinclude MapConvert-response.msg.html

(cl:defclass <MapConvert-response> (roslisp-msg-protocol:ros-message)
  ((status
    :reader status
    :initarg :status
    :type cl:integer
    :initform 0)
   (message
    :reader message
    :initarg :message
    :type cl:string
    :initform ""))
)

(cl:defclass MapConvert-response (<MapConvert-response>)
  ())

(cl:defmethod cl:initialize-instance :after ((m <MapConvert-response>) cl:&rest args)
  (cl:declare (cl:ignorable args))
  (cl:unless (cl:typep m 'MapConvert-response)
    (roslisp-msg-protocol:msg-deprecation-warning "using old message class name fastlio-srv:<MapConvert-response> is deprecated: use fastlio-srv:MapConvert-response instead.")))

(cl:ensure-generic-function 'status-val :lambda-list '(m))
(cl:defmethod status-val ((m <MapConvert-response>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader fastlio-srv:status-val is deprecated.  Use fastlio-srv:status instead.")
  (status m))

(cl:ensure-generic-function 'message-val :lambda-list '(m))
(cl:defmethod message-val ((m <MapConvert-response>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader fastlio-srv:message-val is deprecated.  Use fastlio-srv:message instead.")
  (message m))
(cl:defmethod roslisp-msg-protocol:serialize ((msg <MapConvert-response>) ostream)
  "Serializes a message object of type '<MapConvert-response>"
  (cl:let* ((signed (cl:slot-value msg 'status)) (unsigned (cl:if (cl:< signed 0) (cl:+ signed 4294967296) signed)))
    (cl:write-byte (cl:ldb (cl:byte 8 0) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) unsigned) ostream)
    )
  (cl:let ((__ros_str_len (cl:length (cl:slot-value msg 'message))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) __ros_str_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) __ros_str_len) ostream))
  (cl:map cl:nil #'(cl:lambda (c) (cl:write-byte (cl:char-code c) ostream)) (cl:slot-value msg 'message))
)
(cl:defmethod roslisp-msg-protocol:deserialize ((msg <MapConvert-response>) istream)
  "Deserializes a message object of type '<MapConvert-response>"
    (cl:let ((unsigned 0))
      (cl:setf (cl:ldb (cl:byte 8 0) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) unsigned) (cl:read-byte istream))
      (cl:setf (cl:slot-value msg 'status) (cl:if (cl:< unsigned 2147483648) unsigned (cl:- unsigned 4294967296))))
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
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql '<MapConvert-response>)))
  "Returns string type for a service object of type '<MapConvert-response>"
  "fastlio/MapConvertResponse")
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'MapConvert-response)))
  "Returns string type for a service object of type 'MapConvert-response"
  "fastlio/MapConvertResponse")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql '<MapConvert-response>)))
  "Returns md5sum for a message object of type '<MapConvert-response>"
  "27938b198ec2a6b94cdc450d4db81e6d")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql 'MapConvert-response)))
  "Returns md5sum for a message object of type 'MapConvert-response"
  "27938b198ec2a6b94cdc450d4db81e6d")
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql '<MapConvert-response>)))
  "Returns full string definition for message of type '<MapConvert-response>"
  (cl:format cl:nil "int32 status~%string message~%~%~%"))
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql 'MapConvert-response)))
  "Returns full string definition for message of type 'MapConvert-response"
  (cl:format cl:nil "int32 status~%string message~%~%~%"))
(cl:defmethod roslisp-msg-protocol:serialization-length ((msg <MapConvert-response>))
  (cl:+ 0
     4
     4 (cl:length (cl:slot-value msg 'message))
))
(cl:defmethod roslisp-msg-protocol:ros-message-to-list ((msg <MapConvert-response>))
  "Converts a ROS message object to a list"
  (cl:list 'MapConvert-response
    (cl:cons ':status (status msg))
    (cl:cons ':message (message msg))
))
(cl:defmethod roslisp-msg-protocol:service-request-type ((msg (cl:eql 'MapConvert)))
  'MapConvert-request)
(cl:defmethod roslisp-msg-protocol:service-response-type ((msg (cl:eql 'MapConvert)))
  'MapConvert-response)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'MapConvert)))
  "Returns string type for a service object of type '<MapConvert>"
  "fastlio/MapConvert")