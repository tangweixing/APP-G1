// Auto-generated. Do not edit!

// (in-package xju_pnc.srv)


"use strict";

const _serializer = _ros_msg_utils.Serialize;
const _arraySerializer = _serializer.Array;
const _deserializer = _ros_msg_utils.Deserialize;
const _arrayDeserializer = _deserializer.Array;
const _finder = _ros_msg_utils.Find;
const _getByteLength = _ros_msg_utils.getByteLength;

//-----------------------------------------------------------


//-----------------------------------------------------------

class xju_taskRequest {
  constructor(initObj={}) {
    if (initObj === null) {
      // initObj === null is a special case for deserialization where we don't initialize fields
      this.type = null;
      this.command = null;
      this.dir = null;
      this.path_name = null;
      this.map = null;
    }
    else {
      if (initObj.hasOwnProperty('type')) {
        this.type = initObj.type
      }
      else {
        this.type = 0;
      }
      if (initObj.hasOwnProperty('command')) {
        this.command = initObj.command
      }
      else {
        this.command = 0;
      }
      if (initObj.hasOwnProperty('dir')) {
        this.dir = initObj.dir
      }
      else {
        this.dir = '';
      }
      if (initObj.hasOwnProperty('path_name')) {
        this.path_name = initObj.path_name
      }
      else {
        this.path_name = '';
      }
      if (initObj.hasOwnProperty('map')) {
        this.map = initObj.map
      }
      else {
        this.map = '';
      }
    }
  }

  static serialize(obj, buffer, bufferOffset) {
    // Serializes a message object of type xju_taskRequest
    // Serialize message field [type]
    bufferOffset = _serializer.uint8(obj.type, buffer, bufferOffset);
    // Serialize message field [command]
    bufferOffset = _serializer.uint8(obj.command, buffer, bufferOffset);
    // Serialize message field [dir]
    bufferOffset = _serializer.string(obj.dir, buffer, bufferOffset);
    // Serialize message field [path_name]
    bufferOffset = _serializer.string(obj.path_name, buffer, bufferOffset);
    // Serialize message field [map]
    bufferOffset = _serializer.string(obj.map, buffer, bufferOffset);
    return bufferOffset;
  }

  static deserialize(buffer, bufferOffset=[0]) {
    //deserializes a message object of type xju_taskRequest
    let len;
    let data = new xju_taskRequest(null);
    // Deserialize message field [type]
    data.type = _deserializer.uint8(buffer, bufferOffset);
    // Deserialize message field [command]
    data.command = _deserializer.uint8(buffer, bufferOffset);
    // Deserialize message field [dir]
    data.dir = _deserializer.string(buffer, bufferOffset);
    // Deserialize message field [path_name]
    data.path_name = _deserializer.string(buffer, bufferOffset);
    // Deserialize message field [map]
    data.map = _deserializer.string(buffer, bufferOffset);
    return data;
  }

  static getMessageSize(object) {
    let length = 0;
    length += _getByteLength(object.dir);
    length += _getByteLength(object.path_name);
    length += _getByteLength(object.map);
    return length + 14;
  }

  static datatype() {
    // Returns string type for a service object
    return 'xju_pnc/xju_taskRequest';
  }

  static md5sum() {
    //Returns md5sum for a message object
    return '7b540f0264e4fe6b9d43881f6f965366';
  }

  static messageDefinition() {
    // Returns full string definition for message
    return `
    uint8 EXECUTE = 0
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
    
    `;
  }

  static Resolve(msg) {
    // deep-construct a valid message object instance of whatever was passed in
    if (typeof msg !== 'object' || msg === null) {
      msg = {};
    }
    const resolved = new xju_taskRequest(null);
    if (msg.type !== undefined) {
      resolved.type = msg.type;
    }
    else {
      resolved.type = 0
    }

    if (msg.command !== undefined) {
      resolved.command = msg.command;
    }
    else {
      resolved.command = 0
    }

    if (msg.dir !== undefined) {
      resolved.dir = msg.dir;
    }
    else {
      resolved.dir = ''
    }

    if (msg.path_name !== undefined) {
      resolved.path_name = msg.path_name;
    }
    else {
      resolved.path_name = ''
    }

    if (msg.map !== undefined) {
      resolved.map = msg.map;
    }
    else {
      resolved.map = ''
    }

    return resolved;
    }
};

// Constants for message
xju_taskRequest.Constants = {
  EXECUTE: 0,
  RECORD: 1,
  LOAD_TRAFFIC_ROUTE: 2,
  QR_NAV: 3,
  START: 0,
  PAUSE: 1,
  STOP: 2,
  KEEP_TEACH: 1,
  KEEP_COVER_ZZ: 2,
  KEEP_COVER_BS: 3,
  DISCARD: 4,
  KEEP_TRAFFIC_ROUTE: 5,
}

class xju_taskResponse {
  constructor(initObj={}) {
    if (initObj === null) {
      // initObj === null is a special case for deserialization where we don't initialize fields
      this.message = null;
    }
    else {
      if (initObj.hasOwnProperty('message')) {
        this.message = initObj.message
      }
      else {
        this.message = '';
      }
    }
  }

  static serialize(obj, buffer, bufferOffset) {
    // Serializes a message object of type xju_taskResponse
    // Serialize message field [message]
    bufferOffset = _serializer.string(obj.message, buffer, bufferOffset);
    return bufferOffset;
  }

  static deserialize(buffer, bufferOffset=[0]) {
    //deserializes a message object of type xju_taskResponse
    let len;
    let data = new xju_taskResponse(null);
    // Deserialize message field [message]
    data.message = _deserializer.string(buffer, bufferOffset);
    return data;
  }

  static getMessageSize(object) {
    let length = 0;
    length += _getByteLength(object.message);
    return length + 4;
  }

  static datatype() {
    // Returns string type for a service object
    return 'xju_pnc/xju_taskResponse';
  }

  static md5sum() {
    //Returns md5sum for a message object
    return '5f003d6bcc824cbd51361d66d8e4f76c';
  }

  static messageDefinition() {
    // Returns full string definition for message
    return `
    
    string message
    
    
    `;
  }

  static Resolve(msg) {
    // deep-construct a valid message object instance of whatever was passed in
    if (typeof msg !== 'object' || msg === null) {
      msg = {};
    }
    const resolved = new xju_taskResponse(null);
    if (msg.message !== undefined) {
      resolved.message = msg.message;
    }
    else {
      resolved.message = ''
    }

    return resolved;
    }
};

module.exports = {
  Request: xju_taskRequest,
  Response: xju_taskResponse,
  md5sum() { return 'aadab28b2111acdfca066c4f4a5419ef'; },
  datatype() { return 'xju_pnc/xju_task'; }
};
