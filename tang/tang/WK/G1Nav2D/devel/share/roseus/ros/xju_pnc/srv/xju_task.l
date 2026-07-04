;; Auto-generated. Do not edit!


(when (boundp 'xju_pnc::xju_task)
  (if (not (find-package "XJU_PNC"))
    (make-package "XJU_PNC"))
  (shadow 'xju_task (find-package "XJU_PNC")))
(unless (find-package "XJU_PNC::XJU_TASK")
  (make-package "XJU_PNC::XJU_TASK"))
(unless (find-package "XJU_PNC::XJU_TASKREQUEST")
  (make-package "XJU_PNC::XJU_TASKREQUEST"))
(unless (find-package "XJU_PNC::XJU_TASKRESPONSE")
  (make-package "XJU_PNC::XJU_TASKRESPONSE"))

(in-package "ROS")





(intern "*EXECUTE*" (find-package "XJU_PNC::XJU_TASKREQUEST"))
(shadow '*EXECUTE* (find-package "XJU_PNC::XJU_TASKREQUEST"))
(defconstant xju_pnc::xju_taskRequest::*EXECUTE* 0)
(intern "*RECORD*" (find-package "XJU_PNC::XJU_TASKREQUEST"))
(shadow '*RECORD* (find-package "XJU_PNC::XJU_TASKREQUEST"))
(defconstant xju_pnc::xju_taskRequest::*RECORD* 1)
(intern "*LOAD_TRAFFIC_ROUTE*" (find-package "XJU_PNC::XJU_TASKREQUEST"))
(shadow '*LOAD_TRAFFIC_ROUTE* (find-package "XJU_PNC::XJU_TASKREQUEST"))
(defconstant xju_pnc::xju_taskRequest::*LOAD_TRAFFIC_ROUTE* 2)
(intern "*QR_NAV*" (find-package "XJU_PNC::XJU_TASKREQUEST"))
(shadow '*QR_NAV* (find-package "XJU_PNC::XJU_TASKREQUEST"))
(defconstant xju_pnc::xju_taskRequest::*QR_NAV* 3)
(intern "*START*" (find-package "XJU_PNC::XJU_TASKREQUEST"))
(shadow '*START* (find-package "XJU_PNC::XJU_TASKREQUEST"))
(defconstant xju_pnc::xju_taskRequest::*START* 0)
(intern "*PAUSE*" (find-package "XJU_PNC::XJU_TASKREQUEST"))
(shadow '*PAUSE* (find-package "XJU_PNC::XJU_TASKREQUEST"))
(defconstant xju_pnc::xju_taskRequest::*PAUSE* 1)
(intern "*STOP*" (find-package "XJU_PNC::XJU_TASKREQUEST"))
(shadow '*STOP* (find-package "XJU_PNC::XJU_TASKREQUEST"))
(defconstant xju_pnc::xju_taskRequest::*STOP* 2)
(intern "*KEEP_TEACH*" (find-package "XJU_PNC::XJU_TASKREQUEST"))
(shadow '*KEEP_TEACH* (find-package "XJU_PNC::XJU_TASKREQUEST"))
(defconstant xju_pnc::xju_taskRequest::*KEEP_TEACH* 1)
(intern "*KEEP_COVER_ZZ*" (find-package "XJU_PNC::XJU_TASKREQUEST"))
(shadow '*KEEP_COVER_ZZ* (find-package "XJU_PNC::XJU_TASKREQUEST"))
(defconstant xju_pnc::xju_taskRequest::*KEEP_COVER_ZZ* 2)
(intern "*KEEP_COVER_BS*" (find-package "XJU_PNC::XJU_TASKREQUEST"))
(shadow '*KEEP_COVER_BS* (find-package "XJU_PNC::XJU_TASKREQUEST"))
(defconstant xju_pnc::xju_taskRequest::*KEEP_COVER_BS* 3)
(intern "*DISCARD*" (find-package "XJU_PNC::XJU_TASKREQUEST"))
(shadow '*DISCARD* (find-package "XJU_PNC::XJU_TASKREQUEST"))
(defconstant xju_pnc::xju_taskRequest::*DISCARD* 4)
(intern "*KEEP_TRAFFIC_ROUTE*" (find-package "XJU_PNC::XJU_TASKREQUEST"))
(shadow '*KEEP_TRAFFIC_ROUTE* (find-package "XJU_PNC::XJU_TASKREQUEST"))
(defconstant xju_pnc::xju_taskRequest::*KEEP_TRAFFIC_ROUTE* 5)

(defun xju_pnc::xju_taskRequest-to-symbol (const)
  (cond
        ((= const 0) 'xju_pnc::xju_taskRequest::*EXECUTE*)
        ((= const 1) 'xju_pnc::xju_taskRequest::*RECORD*)
        ((= const 2) 'xju_pnc::xju_taskRequest::*LOAD_TRAFFIC_ROUTE*)
        ((= const 3) 'xju_pnc::xju_taskRequest::*QR_NAV*)
        ((= const 0) 'xju_pnc::xju_taskRequest::*START*)
        ((= const 1) 'xju_pnc::xju_taskRequest::*PAUSE*)
        ((= const 2) 'xju_pnc::xju_taskRequest::*STOP*)
        ((= const 1) 'xju_pnc::xju_taskRequest::*KEEP_TEACH*)
        ((= const 2) 'xju_pnc::xju_taskRequest::*KEEP_COVER_ZZ*)
        ((= const 3) 'xju_pnc::xju_taskRequest::*KEEP_COVER_BS*)
        ((= const 4) 'xju_pnc::xju_taskRequest::*DISCARD*)
        ((= const 5) 'xju_pnc::xju_taskRequest::*KEEP_TRAFFIC_ROUTE*)
        (t nil)))

(defclass xju_pnc::xju_taskRequest
  :super ros::object
  :slots (_type _command _dir _path_name _map ))

(defmethod xju_pnc::xju_taskRequest
  (:init
   (&key
    ((:type __type) 0)
    ((:command __command) 0)
    ((:dir __dir) "")
    ((:path_name __path_name) "")
    ((:map __map) "")
    )
   (send-super :init)
   (setq _type (round __type))
   (setq _command (round __command))
   (setq _dir (string __dir))
   (setq _path_name (string __path_name))
   (setq _map (string __map))
   self)
  (:type
   (&optional __type)
   (if __type (setq _type __type)) _type)
  (:command
   (&optional __command)
   (if __command (setq _command __command)) _command)
  (:dir
   (&optional __dir)
   (if __dir (setq _dir __dir)) _dir)
  (:path_name
   (&optional __path_name)
   (if __path_name (setq _path_name __path_name)) _path_name)
  (:map
   (&optional __map)
   (if __map (setq _map __map)) _map)
  (:serialization-length
   ()
   (+
    ;; uint8 _type
    1
    ;; uint8 _command
    1
    ;; string _dir
    4 (length _dir)
    ;; string _path_name
    4 (length _path_name)
    ;; string _map
    4 (length _map)
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; uint8 _type
       (write-byte _type s)
     ;; uint8 _command
       (write-byte _command s)
     ;; string _dir
       (write-long (length _dir) s) (princ _dir s)
     ;; string _path_name
       (write-long (length _path_name) s) (princ _path_name s)
     ;; string _map
       (write-long (length _map) s) (princ _map s)
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; uint8 _type
     (setq _type (sys::peek buf ptr- :char)) (incf ptr- 1)
   ;; uint8 _command
     (setq _command (sys::peek buf ptr- :char)) (incf ptr- 1)
   ;; string _dir
     (let (n) (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4) (setq _dir (subseq buf ptr- (+ ptr- n))) (incf ptr- n))
   ;; string _path_name
     (let (n) (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4) (setq _path_name (subseq buf ptr- (+ ptr- n))) (incf ptr- n))
   ;; string _map
     (let (n) (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4) (setq _map (subseq buf ptr- (+ ptr- n))) (incf ptr- n))
   ;;
   self)
  )

(defclass xju_pnc::xju_taskResponse
  :super ros::object
  :slots (_message ))

(defmethod xju_pnc::xju_taskResponse
  (:init
   (&key
    ((:message __message) "")
    )
   (send-super :init)
   (setq _message (string __message))
   self)
  (:message
   (&optional __message)
   (if __message (setq _message __message)) _message)
  (:serialization-length
   ()
   (+
    ;; string _message
    4 (length _message)
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; string _message
       (write-long (length _message) s) (princ _message s)
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; string _message
     (let (n) (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4) (setq _message (subseq buf ptr- (+ ptr- n))) (incf ptr- n))
   ;;
   self)
  )

(defclass xju_pnc::xju_task
  :super ros::object
  :slots ())

(setf (get xju_pnc::xju_task :md5sum-) "aadab28b2111acdfca066c4f4a5419ef")
(setf (get xju_pnc::xju_task :datatype-) "xju_pnc/xju_task")
(setf (get xju_pnc::xju_task :request) xju_pnc::xju_taskRequest)
(setf (get xju_pnc::xju_task :response) xju_pnc::xju_taskResponse)

(defmethod xju_pnc::xju_taskRequest
  (:response () (instance xju_pnc::xju_taskResponse :init)))

(setf (get xju_pnc::xju_taskRequest :md5sum-) "aadab28b2111acdfca066c4f4a5419ef")
(setf (get xju_pnc::xju_taskRequest :datatype-) "xju_pnc/xju_taskRequest")
(setf (get xju_pnc::xju_taskRequest :definition-)
      "uint8 EXECUTE = 0
uint8 RECORD = 1
uint8 LOAD_TRAFFIC_ROUTE = 2
uint8 QR_NAV = 3

uint8 START = 0
uint8 PAUSE = 1
uint8 STOP = 2

uint8 KEEP_TEACH = 1
uint8 KEEP_COVER_ZZ = 2
uint8 KEEP_COVER_BS = 3
uint8 DISCARD = 4
uint8 KEEP_TRAFFIC_ROUTE = 5 # only support two points for now

uint8 type #EXECUTE RECORD LOAD_TRAFFIC_ROUTE QR_NAV
uint8 command #START PAUSE STOP KEEP_TEACH KEEP_COVER DISCARD KEEP_TRAFFIC_ROUTE
string dir
string path_name
string map
---

string message

")

(setf (get xju_pnc::xju_taskResponse :md5sum-) "aadab28b2111acdfca066c4f4a5419ef")
(setf (get xju_pnc::xju_taskResponse :datatype-) "xju_pnc/xju_taskResponse")
(setf (get xju_pnc::xju_taskResponse :definition-)
      "uint8 EXECUTE = 0
uint8 RECORD = 1
uint8 LOAD_TRAFFIC_ROUTE = 2
uint8 QR_NAV = 3

uint8 START = 0
uint8 PAUSE = 1
uint8 STOP = 2

uint8 KEEP_TEACH = 1
uint8 KEEP_COVER_ZZ = 2
uint8 KEEP_COVER_BS = 3
uint8 DISCARD = 4
uint8 KEEP_TRAFFIC_ROUTE = 5 # only support two points for now

uint8 type #EXECUTE RECORD LOAD_TRAFFIC_ROUTE QR_NAV
uint8 command #START PAUSE STOP KEEP_TEACH KEEP_COVER DISCARD KEEP_TRAFFIC_ROUTE
string dir
string path_name
string map
---

string message

")



(provide :xju_pnc/xju_task "aadab28b2111acdfca066c4f4a5419ef")


