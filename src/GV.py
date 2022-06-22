PROGRAM_STATUS = {"RUNNING": 1, "IDLE": 2, "STOP": 3, "PAUSE": 4}


def init():
    global ProgramStatus

    ProgramStatus = PROGRAM_STATUS["IDLE"]
