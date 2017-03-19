# kkmdrv.py
Драйвер кассы Штрих-М на Python. С разрешения автора взял в работу.

CHANGELOG 
   0.02 : change kkm.Sale
               bprice = pack('l',int(price*100)+chr(0x0)
               replace to
               bprice = pack('l',int((price*10)*10))+chr(0x0)
               because 17719.85*100 = 1771984.9999999998 and int(17719.85*100) = 1771984
               but     (17719.85*10)*10 = 1771985.0 and int((17719.85*10)*10)  = 1771985

               Add DUMMY class
  0.03    replace all *100 into *10*10 
          add function float2100int
  0.04    >>> int((float('17451.46')*10)*10)
          1745145
          Now work with fload same as string

  0.05    add new error's descriptions (intsurfer)
