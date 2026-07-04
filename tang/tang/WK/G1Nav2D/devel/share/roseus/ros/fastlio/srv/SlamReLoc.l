;; Auto-generated. Do not edit!


(when (boundp 'fastlio::SlamReLoc)
  (if (not (find-package "FASTLIO"))
    (make-package "FASTLIO"))
  (shadow 'SlamReLoc (find-package "FASTLIO")))
(unless (find-package "FASTLIO::SLAMRELOC")
  (make-package "FASTLIO::SLAMRELOC"))
(unless (find-package "FASTLIO::SLAMRELOCREQUEST")
  (make-package "FASTLIO::SLAMRELOCREQUEST"))
(unless (find-package "FASTLIO::SLAMRELOCRESPONSE")
  (make-package "FASTLIO::SLAMRELOCRESPONSE"))

(in-package "ROS")





(defclass fastlio::SlamReLocRequest
  :super ros::object
  :slots (_pcd_path _x _y _z _roll _pitch _yaw ))

(defmethod fastlio::SlamReLocRequest
  (:init
   (&key
    ((:pcd_path __pcd_path) "")
    ((:x __x) 0.0)
    ((:y __y) 0.0)
    ((:z __z) 0.0)
    ((:roll __roll) 0.0)
    ((:pitch __pitch) 0.0)
    ((:yaw __yaw) 0.0)
    )
   (send-super :init)
   (setq _pcd_path (string __pcd_path))
   (setq _x (float __x))
   (setq _y (float __y))
   (setq _z (float __z))
   (setq _roll (float __roll))
   (setq _pitch (float __pitch))
   (setq _yaw (float __yaw))
   self)
  (:pcd_path
   (&optional __pcd_path)
   (if __pcd_path (setq _pcd_path __pcd_path)) _pcd_path)
  (:x
   (&optional __x)
   (if __x (setq _x __x)) _x)
  (:y
   (&optional __y)
   (if __y (setq _y __y)) _y)
  (:z
   (&optional __z)
   (if __z (setq _z __z)) _z)
  (:roll
   (&optional __roll)
   (if __roll (setq _roll __roll)) _roll)
  (:pitch
   (&optional __pitch)
   (if __pitch (setq _pitch __pitch)) _pitch)
  (:yaw
   (&optional __yaw)
   (if __yaw (setq _yaw __yaw)) _yaw)
  (:serialization-length
   ()
   (+
    ;; string _pcd_path
    4 (length _pcd_path)
    ;; float32 _x
    4
    ;; float32 _y
    4
    ;; float32 _z
    4
    ;; float32 _roll
    4
    ;; float32 _pitch
    4
    ;; float32 _yaw
    4
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; string _pcd_path
       (write-long (length _pcd_path) s) (princ _pcd_path s)
     ;; float32 _x
       (sys::poke _x (send s :buffer) (send s :count) :float) (incf (stream-count s) 4)
     ;; float32 _y
       (sys::poke _y (send s :buffer) (send s :count) :float) (incf (stream-count s) 4)
     ;; float32 _z
       (sys::poke _z (send s :buffer) (send s :count) :float) (incf (stream-count s) 4)
     ;; float32 _roll
       (sys::poke _roll (send s :buffer) (send s :count) :float) (incf (stream-count s) 4)
     ;; float32 _pitch
       (sys::poke _pitch (send s :buffer) (send s :count) :float) (incf (stream-count s) 4)
     ;; float32 _yaw
       (sys::poke _yaw (send s :buffer) (send s :count) :float) (incf (stream-count s) 4)
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; string _pcd_path
     (let (n) (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4) (setq _pcd_path (subseq buf ptr- (+ ptr- n))) (incf ptr- n))
   ;; float32 _x
     (setq _x (sys::peek buf ptr- :float)) (incf ptr- 4)
   ;; float32 _y
     (setq _y (sys::peek buf ptr- :float)) (incf ptr- 4)
   ;; float32 _z
     (setq _z (sys::peek buf ptr- :float)) (incf ptr- 4)
   ;; float32 _roll
     (setq _roll (sys::peek buf ptr- :float)) (incf ptr- 4)
   ;; float32 _pitch
     (setq _pitch (sys::peek buf ptr- :float)) (incf ptr- 4)
   ;; float32 _yaw
     (setq _yaw (sys::peek buf ptr- :float)) (incf ptr- 4)
   ;;
   self)
  )

(defclass fastlio::SlamReLocResponse
  :super ros::object
  :slots (_status _message ))

(defmethod fastlio::SlamReLocResponse
  (:init
   (&key
    ((:status __status) 0)
    ((:message __message) "")
    )
   (send-super :init)
   (setq _status (round __status))
   (setq _message (string __message))
   self)
  (:status
   (&optional __status)
   (if __status (setq _status __status)) _status)
  (:message
   (&optional __message)
   (if __message (setq _message __message)) _message)
  (:serialization-length
   ()
   (+
    ;; int32 _status
    4
    ;; string _message
    4 (length _message)
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; int32 _status
       (write-long _status s)
     ;; string _message
       (write-long (length _message) s) (princ _message s)
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; int32 _status
     (setq _status (sys::peek buf ptr- :integer)) (incf ptr- 4)
   ;; string _message
     (let (n) (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4) (setq _message (subseq buf ptr- (+ ptr- n))) (incf ptr- n))
   ;;
   self)
  )

(defclass fastlio::SlamReLoc
  :super ros::object
  :slots ())

(setf (get fastlio::SlamReLoc :md5sum-) "aad2501aad91b362151568ebb4dede7c")
(setf (get fastlio::SlamReLoc :datatype-) "fastlio/SlamReLoc")
(setf (get fastlio::SlamReLoc :request) fastlio::SlamReLocRequest)
(setf (get fastlio::SlamReLoc :response) fastlio::SlamReLocResponse)

(defmethod fastlio::SlamReLocRequest
  (:response () (instance fastlio::SlamReLocResponse :init)))

(setf (get fastlio::SlamReLocRequest :md5sum-) "aad2501aad91b362151568ebb4dede7c")
(setf (get fastlio::SlamReLocRequest :datatype-) "fastlio/SlamReLocRequest")
(setf (get fastlio::SlamReLocRequest :definition-)
      "string pcd_path
float32 x
float32 y
float32 z
float32 roll
float32 pitch
float32 yaw
---
int32 status
string message
")

(setf (get fastlio::SlamReLocResponse :md5sum-) "aad2501aad91b362151568ebb4dede7c")
(setf (get fastlio::SlamReLocResponse :datatype-) "fastlio/SlamReLocResponse")
(setf (get fastlio::SlamReLocResponse :definition-)
      "string pcd_path
float32 x
float32 y
float32 z
float32 roll
float32 pitch
float32 yaw
---
int32 status
string message
")



(provide :fastlio/SlamReLoc "aad2501aad91b362151568ebb4dede7c")


