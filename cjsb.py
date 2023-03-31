import os.path
 
class RegAddrCls:
    """
    an entity represents register addr-value pair.
    """
    def __init__(self, addr, value):
        #super(RegAddrCls, self).__init()
        # default value
        self.__addr = 0
        self.__value = 0
        self.__valid = False
        
        self.regAddr = addr
        self.regValue = value
     
   
    @property
    def regAddr(self):
        return self.__addr
    
    @regAddr.setter
    def regAddr(self, addr):
        if isinstance(addr, int):
            self.__addr = addr
        else:
            raise TypeError("@addr must be a number")
             
    @property
    def regValue(self):
        return self.__value
    
    @regValue.setter
    def regValue(self, value):
        if isinstance(value, int):
            self.__value = value
            self.isValid = True
        else:
             raise TypeError("@value must be a number")
    
    @property
    def isValid(self):
        return self.__valid
 
    @isValid.setter
    def isValid(self, valid):
        if isinstance(valid, bool):
            self.__valid = valid
        else:
            raise TypeError("@valid must be True or False")
 
 
def dumpRegArray(regArray):
    if isinstance(regArray, list):
        index = 0
        while index < len(regArray):
            item = regArray[index]
            if isinstance(item, RegAddrCls):
                if item.isValid:
                    print("0x{_addr:08x} - 0x{_value:08x}".format(_addr=item.regAddr, _value=item.regValue))
            index += 1
    else:
        print("@regArray is not list type.")
            
 
# tt for HEX data types.
TT_00_DATA_RECORD = 0x00
TT_01_EOF = 0x01
TT_02_EX_SEG_ADDR_RECORD = 0x02
TT_04_EX_LINEAR_ADDR_RECORD = 0x04
TT_05_START_LINEAR_ADDR_RECORD = 0x05
 
gBaseRegAddr = 0
 
 
def processLine(lineData):
    
    global gBaseRegAddr
    
    # return this array when data contains valid register addr-value pairs.
    regArray = []
    
    # number of data bytes in the record
    ll = 0
    # starting address
    aaaa = 0
    # HEX record type.
    tt = 00
    # data bytes
    dd = []
    # @cc is the checksum read from the file;
    # @checksum is checksum we calibrate the record
    cc = 0
    checkSum = 0
 
    #print(lineData)
    #print(lineData[2:6])
    
    ll = int(lineData[0:2], base=16)
    #print("ll = 0x{_ll:x}".format(_ll=ll))
 
    aaaa = int(lineData[2:6], base=16)
    aaaa_a = int(lineData[2:4], base=16)
    aaaa_b = int(lineData[4:6], base=16)
    #print("aaaa = 0x{_aaaa:x}".format(_aaaa=aaaa))
 
    tt = int(lineData[6:8], base=16)   
    #print("tt = 0x{_tt:x}".format(_tt=tt))
 
    index = 0
    while (index < ll*2):
        item = int(lineData[8+index:(8+index+2)], base=16)
        dd.append(item)
        index += 2
    #print("dataBytes: {_dd}".format(_dd=dd))
    
    cc = int(lineData[8+index:(8+index+2)], base=16)
    #print("cc = {_cc:x}".format(_cc=cc))
    
    #                          ll + aaaa + tt ++ all_data
    checkSum = 0x01 + 0xFF - ( (ll + (aaaa_a + aaaa_b) + tt + sum(dd)) & 0xFF )
    # checkSum should only be 0~255.
    checkSum = checkSum % 256
    #print("checkSum = {_csum:X}".format(_csum=checkSum))
    
    if cc != checkSum:
        print("CC error for this line data:\ncc = {_cc}\ncheckSum = {_chsum}\n{_dd}".format(_cc=cc, _chsum=checkSum, _dd=lineData))
        return None
    
    ###########################  check tt  ####################################
    if tt == TT_01_EOF:
        #print("EOF, no data available.")
        return None
    elif tt == TT_00_DATA_RECORD:
        #print("TT_00_DATA_RECORD")
        index = 0
        
        # register is 4 bytes aligned.
        regNum = int(ll / 4) * 4
        
        while index < regNum:
            #print("index = {_index}".format(_index = index))
            # calculate register address.
            itemAddr = gBaseRegAddr + aaaa + index
            # get register value.
            itemValue = dd[index] + (dd[index+1] << 8)+ (dd[index+2] << 16) + (dd[index+3] << 24)
            
            #regObj = RegAddrCls()
            #regObj.regAddr = itemAddr
            #regObj.regValue = itemValue
            
            regArray.append(RegAddrCls(itemAddr, itemValue))
            index += 4
        
        #dumpRegArray(regArray)
        return regArray
        
    elif tt == TT_02_EX_SEG_ADDR_RECORD:
        #print("TT_02_EX_SEG_ADDR_RECORD")
        
        segAddr = (dd[0] << 12) + (dd[1] << 4)
        print("segAddr = 0x{_seg:08x}".format(_seg=segAddr))
        
        gBaseRegAddr += segAddr
        print("gBaseRegAddr = 0x{_g:x}".format(_g=gBaseRegAddr))
        return None
    elif tt == TT_04_EX_LINEAR_ADDR_RECORD:
        #print("TT_04_EX_LINEAR_ADDR_RECORD")
        if ll != 2:
            print("it must contain 2 data bytes for upper 16 bits address.")
            return None
        
        # update global register base address.
        upAddr = (dd[0] << 8) + dd[1];
        gBaseRegAddr = (upAddr << 16) + aaaa;
        #print("gBaseRegAddr = 0x{_g:x}".format(_g=gBaseRegAddr))
    elif tt == TT_05_START_LINEAR_ADDR_RECORD:
        print("TT_05_START_LINEAR_ADDR_RECORD")
        if ll != 4:
            print("it must contain 4 data bytes for start address of the application.")
            return None
        # TODO: do nothing, we just ignore this type.
        return None
    else:
        #print("TT--Unkown")
        return None
 
 
def fileHex2Txt(filepath):
    """
    @filepath input file must be HEX format, which is generated from Keil debug
              command: "SAVE filepath start_addr, end_addr, 0x4"
    """
    if not isinstance(filepath, str):
        print("@filepath must be subclass of str.")
        return
 
    regSet = []
 
    with open(filepath, 'rt') as fileObj:
        while True:
            line = fileObj.readline()
            if len(line):
                # remove ':'
                line = line.replace(':', '').strip()
                tempSet = processLine(line)
                if tempSet != None:
                    regSet += tempSet
            else:
                break
    
    inputAbsPath = os.path.abspath(filepath)
    outputFilepath = inputAbsPath.split('.')[0] + '.txt'
    print(" input filepath = {_in}".format(_in=inputAbsPath))
    print("output filepath = {_out}".format(_out=outputFilepath))
        
    #dumpRegArray(regSet)
    
    with open(outputFilepath, 'wt') as fileObj:
        fileObj.write("  address ---  value\n")
        index = 0
        while index < len(regSet):
            addr = regSet[index].regAddr
            val = regSet[index].regValue
            fileObj.write("0x{_addr:08x} - 0x{_val:08x}\n".format(_addr=addr, _val=val))
            index += 1    
 
 
def convertHex386ToTxt(filepath):
    
    # check file suffix
    suffix = os.path.basename(filepath).split('.')[1]
    if suffix != 'hex':
        print("file must have 'hex' suffix")
        return
    
    # check if file exists.
    hex_file_path = os.path.abspath(filepath)
    if os.path.exists(hex_file_path):
        fileHex2Txt(hex_file_path)
    else:
        print("file does NOT exist: {_f}".format(_f=hex_file_path))
    
 
def main():
    print("------  main()  start  ------")
    
    convertHex386ToTxt("DATA.hex")
    
    print("------  main()   over  ------")
 
 
if __name__ == "__main__":
    main()