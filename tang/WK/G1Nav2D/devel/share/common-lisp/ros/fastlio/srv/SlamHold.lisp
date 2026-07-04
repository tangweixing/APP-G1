; Auto-generated. Do not edit!


(cl:in-package fastlio-srv)


;//! \htmlinclude SlamHold-request.msg.html

(cl:defclass <SlamHold-request> (roslisp-msg-protocol:ros-message)
  ((code
    :reader code
    :initarg :code
    :type cl:integer
    :initform 0))
)

(cl:defclass SlamHold-request (<SlamHold-request>)
  ())

(cl:defmethod cl:initialize-instance :after ((m <SlamHold-request>) cl:&rest args)
  (cl:declare (cl:ignorable args))
  (cl:unless (cl:typep m 'SlamHold-request)
    (roslisp-msg-protocol:msg-deprecation-warning "using old message class name fastlio-srv:<SlamHold-request> is deprecated: use fastlio-srv:SlamHold-request instead.")))

(cl:ensure-generic-function 'code-val :lambda-list '(m))
(cl:defmethod code-val ((m <SlamHold-request>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader fastlio-srv:code-val is deprecated.  Use fastlio-srv:code instead.")
  (code m))
(cl:defmethod roslisp-msg-protocol:serialize ((msg <SlamHold-request>) ostream)
  "Serializes a message object of type '<SlamHold-request>"
  (cl:let* ((signed (cl:slot-value msg 'code)) (unsigned (cl:if (cl:< signed 0) (cl:+ signed 4294967296) signed)))
    (cl:write-byte (cl:ldb (cl:byte 8 0) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) unsigned) ostream)
    )
)
(cl:defmethod roslisp-msg-protocol:deserialize ((msg <SlamHold-request>) istream)
  "Deserializes a message object of type '<SlamHold-request>"
    (cl:let ((unsigned 0))
      (cl:setf (cl:ldb (cl:byte 8 0) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) unsigned) (cl:read-byte istream))
      (cl:setf (cl:slot-value msg 'code) (cl:if (cl:< unsigned 2147483648) unsigned (cl:- unsigned 4294967296))))
  msg
)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql '<SlamHold-request>)))
  "Returns string type for a service object of type '<SlamHold-request>"
  "fastlio/SlamHoldRequest")
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'SlamHold-request)))
  "Returns string type for a service object of type 'SlamHold-request"
  "fastlio/SlamHoldRequest")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql '<SlamHold-request>)))
  "Returns md5sum for a message object of type '<SlamHold-request>"
  "70c3acd228da7b83ec6f69864540ea91")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql 'SlamHold-request)))
  "Returns md5sum for a message object of type 'SlamHold-request"
  "70c3acd228da7b83ec6f69864540ea91")
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql '<SlamHold-request>)))
  "Returns full string definition for message of type '<SlamHold-request>"
  (cl:format cl:nil "int32 code~%~%~%"))
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql 'SlamHold-request)))
  "Returns full string definition for message of type 'SlamHold-request"
  (cl:format cl:nil "int32 code~%~%~%"))
(cl:defmethod roslisp-msg-protocol:serialization-length ((msg <SlamHold-request>))
  (cl:+ 0
     4
))
(cl:defmethod roslisp-msg-protocol:ros-message-to-list ((msg <SlamHold-request>))
  "Converts a ROS message object to a list"
  (cl:list 'SlamHold-request
    (cl:cons ':code (code msg))
))
;//! \htmlinclude SlamHold-response.msg.html

(cl:defclass <SlamHold-response> (roslisp-msg-protocol:ros-message)
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

(cl:defclass SlamHold-response (<SlamHold-response>)
  ())

(cl:defmethod cl:initialize-instance :after ((m <SlamHold-response>) cl:&rest args)
  (cl:declare (cl:ignorable args))
  (cl:unless (cl:typep m 'SlamHold-response)
    (roslisp-msg-protocol:msg-deprecation-warning "using old message class name fastlio-srv:<SlamHold-response> is deprecated: use fastlio-srv:SlamHold-response instead.")))

(cl:ensure-generic-function 'status-val :lambda-list '(m))
(cl:defmethod status-val ((m <SlamHold-response>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader fastlio-srv:status-val is deprecated.  Use fastlio-srv:status instead.")
  (status m))

(cl:ensure-generic-function 'message-val :lambda-list '(m))
(cl:defmethod message-val ((m <SlamHold-response>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader fastlio-srv:message-val is deprecated.  Use fastlio-srv:message instead.")
  (message m))
(cl:defmethod roslisp-msg-protocol:serialize ((msg <SlamHold-response>) ostream)
  "Serializes a message object of type '<SlamHold-response>"
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
(cl:defmethod roslisp-msg-protocol:deserialize ((msg <SlamHold-response>) istream)
  "Deserializes a message object of type '<SlamHold-response>"
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
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql '<SlamHold-response>)))
  "Returns string type for a service object of type '<SlamHold-response>"
  "fastlio/SlamHoldResponse")
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'SlamHold-response)))
  "Returns string type for a service object of type 'SlamHold-response"
  "fastlio/SlamHoldResponse")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql '<SlamHold-response>)))
  "Returns md5sum for a message object of type '<SlamHold-response>"
  "70c3acd228da7b83ec6f69864540ea91")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql 'SlamHold-response)))
  "Returns md5sum for a message object of type 'SlamHold-response"
  "70c3acd228da7b83ec6f69864540ea91")
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql '<SlamHold-response>)))
  "Returns full string definition for message of type '<SlamHold-response>"
  (cl:format cl:nil "int32 status~%string message~%~%~%~%"))
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql 'SlamHold-response)))
  "Returns full string definition for message of type 'SlamHold-response"
  (cl:format cl:nil "int32 status~%string message~%~%~%~%"))
(cl:defmethod roslisp-msg-protocol:serialization-length ((msg <SlamHold-response>))
  (cl:+ 0
     4
     4 (cl:length (cl:slot-value msg 'message))
))
(cl:defmethod roslisp-msg-protocol:ros-message-to-list ((msg <SlamHold-response>))
  "Converts a ROS message object to a list"
  (cl:list 'SlamHold-response
    (cl:cons ':status (status msg))
    (cl:cons ':message (message msg))
))
(cl:defmethod roslisp-msg-protocol:service-request-type ((msg (cl:eql 'SlamHold)))
  'SlamHold-request)
(cl:defmethod roslisp-msg-protocol:service-response-type ((msg (cl:eql 'SlamHold)))
  'SlamHold-response)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'SlamHold)))
  "Returns string type for a service object of type '<SlamHold>"
  "fastlio/SlamHold")