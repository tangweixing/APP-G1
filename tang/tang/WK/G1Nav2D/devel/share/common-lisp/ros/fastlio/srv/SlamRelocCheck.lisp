; Auto-generated. Do not edit!


(cl:in-package fastlio-srv)


;//! \htmlinclude SlamRelocCheck-request.msg.html

(cl:defclass <SlamRelocCheck-request> (roslisp-msg-protocol:ros-message)
  ((code
    :reader code
    :initarg :code
    :type cl:boolean
    :initform cl:nil))
)

(cl:defclass SlamRelocCheck-request (<SlamRelocCheck-request>)
  ())

(cl:defmethod cl:initialize-instance :after ((m <SlamRelocCheck-request>) cl:&rest args)
  (cl:declare (cl:ignorable args))
  (cl:unless (cl:typep m 'SlamRelocCheck-request)
    (roslisp-msg-protocol:msg-deprecation-warning "using old message class name fastlio-srv:<SlamRelocCheck-request> is deprecated: use fastlio-srv:SlamRelocCheck-request instead.")))

(cl:ensure-generic-function 'code-val :lambda-list '(m))
(cl:defmethod code-val ((m <SlamRelocCheck-request>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader fastlio-srv:code-val is deprecated.  Use fastlio-srv:code instead.")
  (code m))
(cl:defmethod roslisp-msg-protocol:serialize ((msg <SlamRelocCheck-request>) ostream)
  "Serializes a message object of type '<SlamRelocCheck-request>"
  (cl:write-byte (cl:ldb (cl:byte 8 0) (cl:if (cl:slot-value msg 'code) 1 0)) ostream)
)
(cl:defmethod roslisp-msg-protocol:deserialize ((msg <SlamRelocCheck-request>) istream)
  "Deserializes a message object of type '<SlamRelocCheck-request>"
    (cl:setf (cl:slot-value msg 'code) (cl:not (cl:zerop (cl:read-byte istream))))
  msg
)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql '<SlamRelocCheck-request>)))
  "Returns string type for a service object of type '<SlamRelocCheck-request>"
  "fastlio/SlamRelocCheckRequest")
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'SlamRelocCheck-request)))
  "Returns string type for a service object of type 'SlamRelocCheck-request"
  "fastlio/SlamRelocCheckRequest")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql '<SlamRelocCheck-request>)))
  "Returns md5sum for a message object of type '<SlamRelocCheck-request>"
  "6fa8ef0c716a8f69e2ee4f999bd02a6e")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql 'SlamRelocCheck-request)))
  "Returns md5sum for a message object of type 'SlamRelocCheck-request"
  "6fa8ef0c716a8f69e2ee4f999bd02a6e")
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql '<SlamRelocCheck-request>)))
  "Returns full string definition for message of type '<SlamRelocCheck-request>"
  (cl:format cl:nil "bool code~%~%~%"))
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql 'SlamRelocCheck-request)))
  "Returns full string definition for message of type 'SlamRelocCheck-request"
  (cl:format cl:nil "bool code~%~%~%"))
(cl:defmethod roslisp-msg-protocol:serialization-length ((msg <SlamRelocCheck-request>))
  (cl:+ 0
     1
))
(cl:defmethod roslisp-msg-protocol:ros-message-to-list ((msg <SlamRelocCheck-request>))
  "Converts a ROS message object to a list"
  (cl:list 'SlamRelocCheck-request
    (cl:cons ':code (code msg))
))
;//! \htmlinclude SlamRelocCheck-response.msg.html

(cl:defclass <SlamRelocCheck-response> (roslisp-msg-protocol:ros-message)
  ((status
    :reader status
    :initarg :status
    :type cl:boolean
    :initform cl:nil))
)

(cl:defclass SlamRelocCheck-response (<SlamRelocCheck-response>)
  ())

(cl:defmethod cl:initialize-instance :after ((m <SlamRelocCheck-response>) cl:&rest args)
  (cl:declare (cl:ignorable args))
  (cl:unless (cl:typep m 'SlamRelocCheck-response)
    (roslisp-msg-protocol:msg-deprecation-warning "using old message class name fastlio-srv:<SlamRelocCheck-response> is deprecated: use fastlio-srv:SlamRelocCheck-response instead.")))

(cl:ensure-generic-function 'status-val :lambda-list '(m))
(cl:defmethod status-val ((m <SlamRelocCheck-response>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader fastlio-srv:status-val is deprecated.  Use fastlio-srv:status instead.")
  (status m))
(cl:defmethod roslisp-msg-protocol:serialize ((msg <SlamRelocCheck-response>) ostream)
  "Serializes a message object of type '<SlamRelocCheck-response>"
  (cl:write-byte (cl:ldb (cl:byte 8 0) (cl:if (cl:slot-value msg 'status) 1 0)) ostream)
)
(cl:defmethod roslisp-msg-protocol:deserialize ((msg <SlamRelocCheck-response>) istream)
  "Deserializes a message object of type '<SlamRelocCheck-response>"
    (cl:setf (cl:slot-value msg 'status) (cl:not (cl:zerop (cl:read-byte istream))))
  msg
)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql '<SlamRelocCheck-response>)))
  "Returns string type for a service object of type '<SlamRelocCheck-response>"
  "fastlio/SlamRelocCheckResponse")
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'SlamRelocCheck-response)))
  "Returns string type for a service object of type 'SlamRelocCheck-response"
  "fastlio/SlamRelocCheckResponse")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql '<SlamRelocCheck-response>)))
  "Returns md5sum for a message object of type '<SlamRelocCheck-response>"
  "6fa8ef0c716a8f69e2ee4f999bd02a6e")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql 'SlamRelocCheck-response)))
  "Returns md5sum for a message object of type 'SlamRelocCheck-response"
  "6fa8ef0c716a8f69e2ee4f999bd02a6e")
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql '<SlamRelocCheck-response>)))
  "Returns full string definition for message of type '<SlamRelocCheck-response>"
  (cl:format cl:nil "bool status~%~%~%"))
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql 'SlamRelocCheck-response)))
  "Returns full string definition for message of type 'SlamRelocCheck-response"
  (cl:format cl:nil "bool status~%~%~%"))
(cl:defmethod roslisp-msg-protocol:serialization-length ((msg <SlamRelocCheck-response>))
  (cl:+ 0
     1
))
(cl:defmethod roslisp-msg-protocol:ros-message-to-list ((msg <SlamRelocCheck-response>))
  "Converts a ROS message object to a list"
  (cl:list 'SlamRelocCheck-response
    (cl:cons ':status (status msg))
))
(cl:defmethod roslisp-msg-protocol:service-request-type ((msg (cl:eql 'SlamRelocCheck)))
  'SlamRelocCheck-request)
(cl:defmethod roslisp-msg-protocol:service-response-type ((msg (cl:eql 'SlamRelocCheck)))
  'SlamRelocCheck-response)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'SlamRelocCheck)))
  "Returns string type for a service object of type '<SlamRelocCheck>"
  "fastlio/SlamRelocCheck")