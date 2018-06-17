for serial in range(1, 10):
    print(f'CreatePair p{serial} p{serial} -qdp -hdp -type Sapphire -version 14.5000.00000 -serialNumber {serial}')
    print(f'OperateDevice Wireless p{serial} ENABLE')
    print(f'operatedevice connection p{serial} connect')
    print()


prog_name = 'prog_1'
pump_serial = 1

for p in range(30, 35):
    pid = str(p)
    pump_name = 'inf_pump_' + pid
    prog_name = 'Prog_' + pid
    dose = 'dose' + pid
    serial = p
    command = f'''
CreatePair {pump_name} {pump_name} -hdp -qdp -live -record -type Sapphire -version 14.50.00 -serialNumber {serial}
OperateDevice Wireless {pump_name} ENABLE
OperateDevice Connection {pump_name} CONNECT
CreateDose RateDose {dose} {100+p} {100+p} MDC_DIM_MILLI_L_PER_HR
CreateProgram Continuous {prog_name} {dose}
OperateDevice loadprogram {pump_name} CHANNEL_A {prog_name}
OperateDevice ProgramChannel -override {pump_name} CHANNEL_A ACCEPT
OperateDevice Infusion {pump_name} CHANNEL_A start
    '''

    print(command)
