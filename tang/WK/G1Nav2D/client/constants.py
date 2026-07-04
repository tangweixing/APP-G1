from enum import Enum


ACTION={
    "Damp": 1001,
    "Balancesstand": 1002,
    "StopMove": 1003,
    "StandUp": 1004,
    "StandDown": 1005,
    "RecoveryStand": 1006,
    "Sit": 1009,
    "Risesit": 1010,
    "Hello": 1016,
    "Stretch": 1017,
    "Dance1": 1022,
    "Dance2": 1023,
    "Scrape": 1029,
    "FrontJump": 1031,
    "FrontPounce": 1032,
    "FingerHeart": 1036,
    "StaticWalk": 1061, # jing dian 
    "TrotRun": 1062, # pao bu
    "EconomicGait": 1063, # chang gui
    "HandStand": 2044,
    "FrontFlip": 1030,
    "BackFlip": 2043,
    "LeftFlip": 2041,
    "WalkStair": 2049, #ling dong  default
    "BackStand": 2050,
    "CrossStep": 2051,

}
SPORT_CMD = {
    "Damp": 1001,
    "Balancesstand": 1002,
    "StopMove": 1003,
    "StandUp": 1004,
    "StandDown": 1005,
    "RecoveryStand": 1006,
    "Euler": 1007,
    "Move": 1008,
    "Sit": 1009,
    "Risesit": 1010,
    "BodyHeight": 1013,
    "FootRaiseHeight": 1014,
    "SpeedLevel": 1015,
    "Hello": 1016,
    "Stretch": 1017,
    "Dance1": 1022,
    "Dance2": 1023,
    "SwitchJoystick": 1027,
    "Pose": 1028,
    "Scrape": 1029,
    "FrontJump": 1031,
    "FrontPounce": 1032,
    "FingerHeart": 1036,
    "StaticWalk": 1061, # jing dian 
    "TrotRun": 1062, # pao bu
    "EconomicGait": 1063, # chang gui
    "HandStand": 2044,
    "FrontFlip": 1030,
    "BackFlip": 2043,
    "LeftFlip": 2041,
    "FreeWalk": 2045,
    "FreeBound": 2046,
    "FreeJump": 2047,
    "FreeAvoid": 2048,  # Note: Original had "FreeWorld" mapping to "FreeAvoid"
    "WalkStair": 2049, #ling dong  default
    "BackStand": 2050,
    "CrossStep": 2051,
    "LeadFollow": 2056,
    "SwitchGait": 1011,
}



GAIT={
    "Normal":1,
    "Run":2,
    "Upstair":3,
    "Downstair":4,
}

MOTION={
    "AI mode":"ai",
    "NORMAL mode":"normal",
    "ADVANCED mode":"advanced"
}