#!/usr/bin/python
# -*- coding: utf8 -*-
"""
Shtrikh FR-K Python interface
=================================================================
Copyright (C) 2010  Dmitry Shamov demmsnt@gmail.com

    You can choose between two licenses when using this package:
    1) GNU GPLv2
    2) PSF license for Python 2.2

    Shtrikh KKM page: http://www.shtrih-m.ru/
        Project page: http://sourceforge.net/projects/pyshtrih/

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

  0.05    add new error's descriptions
"""

VERSION = 0.04
PORT = '/dev/ttyACM0' #'COM1'
#Commands
DEBUG = 1
TODO  = 1
OS_CP = 'cp866'

def dbg(*a):
        if DEBUG:
                print unicode(string.join(map(lambda x: str(x),a)),'utf8').encode(OS_CP)

def todo(*a):
        if TODO:
                print unicode(string.join(map(lambda x: str(x),a)),'utf8').encode(OS_CP)

import serial
import string,time
from struct import pack, unpack


def bufStr(*b):
    """Преобразует буфер 16-х значений в строку"""
    result = []
    for x in b: result.append(chr(x))
    return string.join(result,'')

def hexStr(s):
    """Преобразуем в 16-е значения"""
    result = []
    for c in s: result.append(hex(ord(c)))
    return string.join(result,' ')

def float2100int(f,digits=2):
        mask = "%."+str(digits)+'f'
        s    = mask % f
        return int(s.replace('.',''))

#Status constants
OK            = 0
KKM_READY     = 1
KKM_ANSWERING = 2
#FP modes descriptions
FP_MODES_DESCR = { 0:u'Принтер в рабочем режиме.',\
                   1:u'Выдача данных.',\
                   2:u'Открытая смена, 24 часа не кончились.',\
                   3:u'Открытая смена, 24 часа кончились.',\
                   4:u'Закрытая смена.',\
                   5:u'Блокировка по неправильному паролю налогового инспектора.',\
                   6:u'Ожидание подтверждения ввода даты.',\
                   7:u'Разрешение изменения положения десятичной точки.',\
                   8:u'Открытый документ:',\
                   9:u'''Режим разрешения технологического обнуления. В этот режим ККМ переходит по включению питания, если некорректна информация в энергонезависимом ОЗУ ККМ.''',\
                   10:u'Тестовый прогон.',\
                   11:u'Печать полного фис. отчета.',\
                   12:u'Печать отчёта ЭКЛЗ.',\
                   13:u'Работа с фискальным подкладным документом:',\
                   14:u'Печать подкладного документа.',\
                   15:u'Фискальный подкладной документ сформирован.',\
                   208:u'Отчет операционного журнала не распечатан!'}

FR_SUBMODES_DESCR = {0:{0:u'Подрежим не предусмотрен'},\
                     1:{0:u'Подрежим не предусмотрен'},\
                     2:{0:u'Подрежим не предусмотрен'},\
                     3:{0:u'Подрежим не предусмотрен'},\
                     4:{0:u'Подрежим не предусмотрен'},\
                     5:{0:u'Подрежим не предусмотрен'},\
                     6:{0:u'Подрежим не предусмотрен'},\
                     7:{0:u'Подрежим не предусмотрен'},\
                     8:{0:u'Продажа',\
                        1:u'Покупка',\
                        2:u'Возврат продажи',\
                        3:u'Возврат покупки',\
			4:u'Нефискальный'},\
                     9:{0:u'Подрежим не предусмотрен'},\
                     10:{0:u'Подрежим не предусмотрен'},\
                     11:{0:u'Подрежим не предусмотрен'},\
                     12:{0:u'Подрежим не предусмотрен'},\
                     13:{0:u'Продажа (открыт)',\
                        1:u'Покупка (открыт)',\
                        2:u'Возврат продажи (открыт)',\
                        3:u'Возврат покупки (открыт)'},\
                     14:{0:u'Ожидание загрузки.',\
                         1:u'Загрузка и позиционирование.',\
                         2:u'Позиционирование.',\
                         3:u'Печать.',\
                         4:u'Печать закончена.',\
                         5:u'Выброс документа.',\
                         6:u'Ожидание извлечения.'},\
                     15:{0:u'Подрежим не предусмотрен'}}


ENQ = chr(0x05)
STX = chr(0x02)
ACK = chr(0x06)
NAK = chr(0x15)

MAX_TRIES = 10 # Кол-во попыток
MIN_TIMEOUT = 0.05

DEFAULT_ADM_PASSWORD = bufStr(0x1e,0x0,0x0,0x0) #Пароль админа по умолчанию = 30
DEFAULT_PASSWORD     = bufStr(0x1,0x0,0x0,0x0)  #Пароль кассира по умолчанию = 1

def LRC(buff):
    """Подсчет CRC"""
    result = 0
    for c in buff:
        result = result ^ ord(c)
    dbg( "LRC",result)
    return chr(result)

def byte2array(b):
        """Convert byte into array"""
        result = []
        for i in range(0,8):
                if b == b >> 1 <<1:
                        result.append(False)
                else:
                        result.append(True)
                b = b >>1
        return result


#Exceptions
class kkmException(Exception):
        def __init__(self, value):
                self.value = value
                print('kkm exception='+str(self.value))
                self.s = { 0x1: "Неизвестная команда, неверный формат посылки или неизвестные параметры (ошибка 0x1)",\
			   0x2: "Неверное состояние ФН (0x2)",\
			   0x3: "Ошибка ФН (0x3)",\
			   0x4: "Ошибка KC (0x4)",\
			   0x5: "Закончен срок эксплуатации ФН (0x5)",\
			   0x6: "Архив ФН переполнен (0x6)",\
			   0x7: "Неверные дата и/или время (0x7)",\
			   0x8: "Нет запрошенных данных (0x8)",\
			   0x9: "Некорректное значение параметров команды (0x9)",\
			   0x10: "Превышение размеров TLV данных (0x10)",\
			   0x11: "Нет транспортного соединения (0x11)",\
			   0x12: "Исчерпан ресурс КС (криптографического сопроцессора) (0x12)",\
			   0x14: "Исчерпан ресурс хранения (0x14)",\
			   0x15: "Исчерпан ресурс Ожидания передачи сообщения (0x15)",\
			   0x16: "Продолжительность смены более 24 часов (0x16)",\
			   0x17: "Неверная разница во времени между 2 операцими (0x17)",\
			   0x20: "Сообщение от ОФД не может быть принято (0x20)",\
			   0x26: "Вносимая клиентом сумма меньше суммы чека (0x26)",\
			   0x2b: "Невозможно отменить предыдущую команду (0x2b)",\
			   0x2c: "Обнулённая касса (повторное гашение невозможно) (0x2c)",\
			   0x2d: "Сумма чека по секции меньше суммы сторно (0x2d)",\
			   0x2e: "В ККТ нет денег для выплаты (0x2e)",\
			   0x30: "ККТ заблокирован, ждет ввода пароля налогового инспектора (0x30)",\
			   0x32: "Требуется выполнение общего гашения (0x32)",\
			   0x33: "Некорректные параметры в команде (0x33)",\
			   0x34: "Нет данных (0x34)",\
			   0x35: "Некорректный параметр при данных настройках (0x35)",\
			   0x36: "Некорректные параметры в команде для данной реализации ККТ (0x36)",\
			   0x37: "Команда не поддерживается в данной реализации ККТ (0x37)",\
			   0x38: "Ошибка в ПЗУ (0x38)",\
			   0x39: "Внутренняя ошибка ПО ККТ (0x39)",\
			   0x3a: "Переполнение накопления по надбавкам в смене (0x3a)",\
			   0x3b: "Переполнение накопления в смене (0x3b)",\
			   0x3c: "Смена открыта – операция невозможна (0x3c)",\
			   0x3d: "Смена не открыта – операция невозможна (0x3d)",\
			   0x3e: "Переполнение накопления по секциям в смене (0x3e)",\
			   0x3f: "Переполнение накопления по скидкам в смене (0x3f)",\
			   0x40: "Переполнение диапазона скидок (0x40)",\
			   0x41: "Переполнение диапазона оплаты наличными (0x41)",\
			   0x42: "Переполнение диапазона оплаты типом 2 (0x42)",\
			   0x43: "Переполнение диапазона оплаты типом 3 (0x43)",\
			   0x44: "Переполнение диапазона оплаты типом 4 (0x44)",\
			   0x45: "Cумма всех типов оплаты меньше итога чека (0x45)",\
			   0x46: "Не хватает наличности в кассе (0x46)",\
			   0x47: "Переполнение накопления по налогам в смене (0x47)",\
			   0x48: "Переполнение итога чека (0x48)",\
			   0x49: "Операция невозможна в открытом чеке данного типа (0x49)",\
			   0x4a: "Открыт чек – операция невозможна (0x4a)",\
                           0x4b: "Буфер чека переполнен (0x4b)",\
			   0x4c: "Переполнение накопления по обороту налогов в смене (0x4c)",\
                           0x4d: "Вносимая безналичной оплатой сумма больше суммы чека (0x4d)",\
			   0x4e: "Смена превысила 24 часа (Закройте смену с гашением) (0x4e)",\
                           0x4f: "Неверный пароль (0x4f)",\
			   0x50: "Идет печать результатов выполнения предыдущей команды (0x50)",\
			   0x51: "Переполнение накоплений наличными в смене (0x51)",\
			   0x52: "Переполнение накоплений по типу оплаты 2 в смене (0x52)",\
			   0x53: "Переполнение накоплений по типу оплаты 3 в смене (0x53)",\
			   0x54: "Переполнение накоплений по типу оплаты 4 в смене (0x54)",\
			   0x55: "Чек закрыт – операция невозможна (0x55)",\
			   0x56: "Нет документа для повтора (0x56)",\
			   0x58: "Ожидание команды продолжения печати (0x58)",\
			   0x59: "Документ открыт другим кассиром (0x59)",\
			   0x5a: "Скидка превышает накопления в чеке (0x5a)",\
                           0x5b: "Переполнение диапазона надбавок (0x5b)",\
			   0x5c: "Понижено напряжение 24В (0x5c)",\
                           0x5d: "Таблица не определена (0x5d)",\
			   0x5e: "Неверная операция (0x5e)",\
                           0x5f: "Отрицательный итог чека (0x5f)",\
			   0x60: "Переполнение при умножении (0x60)",\
			   0x61: "Переполнение диапазона цены (0x61)",\
			   0x62: "Переполнение диапазона количества (0x62)",\
			   0x63: "Переполнение диапазона отдела (0x63)",\
			   0x65: "Не хватает денег в секции (0x65)",\
			   0x66: "Переполнение денег в секции (0x66)",\
			   0x68: "Не хватает денег по обороту налогов (0x68)",\
			   0x69: "Переполнение денег по обороту налогов (0x69)",\
			   0x6a: "Ошибка питания в момент ответа по I2C (0x6a)",\
                           0x6b: "Нет чековой ленты (0x6b)",\
			   0x6c: "Нет операционного журнала (0x6c)",\
                           0x6d: "Не хватает денег по налогу (0x6d)",\
			   0x6e: "Переполнение денег по налогу (0x6e)",\
                           0x6f: "Переполнение по выплате в смене (0x6f)",\
			   0x71: "Ошибка отрезчика (0x71)",\
			   0x72: "Команда не поддерживается в данном подрежиме (0x72)",\
                           0x73: "Команда не поддерживается в данном режиме (отмените печать чека или продолжите её или закончилась смена, надо осуществить гашение.) (0x73)",\
                           0x74: "Ошибка ОЗУ (0x74)",\
                           0x75: "Ошибка питания (0x75)",\
                           0x76: "Ошибка принтера: нет импульсов с тахогенератора (0x76)",\
                           0x77: "Ошибка принтера: нет сигнала с датчиков (0x77)",\
                           0x78: "Замена ПО (0x78)",\
                           0x7a: "Поле не редактируется (0x7a)",\
                           0x7b: "Ошибка оборудования (0x7b)",\
                           0x7c: "Не совпадает дата (0x7c)",\
                           0x7d: "Неверный формат даты (0x7d)",\
                           0x7e: "Неверное значение в поле длины (0x7e)",\
                           0x7f: "Переполнение диапазона итога чека (0x7f)",\
                           0x84: "Переполнение наличности (0x84)",\
                           0x85: "Переполнение по приходу в смене (0x85)",\
                           0x86: "Переполнение по расходу в смене (0x86)",\
                           0x87: "Переполнение по возвратам прихода в смене (0x87)",\
                           0x88: "Переполнение по возвратам расхода в смене (0x88)",\
                           0x89: "Переполнение по внесению в смене (0x89)",\
                           0x8a: "Переполнение по надбавкам в чеке (0x8a)",\
                           0x8b: "Переполнение по скидкам в чеке (0x8b)",\
                           0x8c: "Отрицательный итог надбавки в чеке (0x8c)",\
                           0x8d: "Отрицательный итог скидки в чеке (0x8d)",\
                           0x8e: "Нулевой итог чека (0x8e)",\
                           0x8f: "Касса не зарегистрирована (0x8f)",\
			   0x90: "Поле превышает размер, установленный в настройках (0x90)",\
			   0x91: "Выход за границу поля печати при данных настройках шрифта (0x91)",\
			   0x92: "Наложение полей (0x92)",\
			   0x93: "Восстановление ОЗУ прошло успешно (0x93)",\
			   0x94: "Исчерпан лимит операций в чеке (0x94)",\
			   0x96: "Выполните отчет о закрытии смены (0x96)",\
                           0x9b: "Некорректное действие (0x9b)",\
			   0x9c: "Товар не найден по коду в базе товаров (0x9c)",\
                           0x9d: "Неверные данные в записе о товаре вxбазе товаров (0x9d)",\
			   0x9e: "Неверный размер файла базы или регистров товаров (0x9e)",\
			   0xc0: "Контроль даты и времени (подтвердите дату и время) (0xc0)",\
			   0xc2: "Превышение напряжения в блоке питания (0xc2)",\
			   0xc4: "Несовпадение номеров смен (0xc4)",\
			   0xc5: "Буфер подкладного документа пуст (0xc5)",\
			   0xc6: "Подкладной документ отсутствует (0xc6)",\
			   0xc7: "Поле не редактируется в данном режиме (0xc7)",\
                           0xc8: "Нет связи с принтером или отсутствуют импульсы от таходатчика (0xc8)",\
			   0xc9: "Перегрев печатающей головки (0xc9)",\
                           0xca: "Температура вне условий эксплуатации (0xca)",\
			   0xcb: "Неверный подытог чека (0xcb)",\
                           0xce: "Лимит минимального свободного объема ОЗУ или ПЗУ на ККТ исчерпан (0xce)",\
			   0xcf: "Неверная дата (Часы сброшены? Установите дату!) (0xcf)",\
			   0xd0: "Отчет операционного журнала не распечатан! (0xd0)",\
			   0xd1: "Нет данных в буфере (0xd1)",\
                           0xd5: "Критическая ошибка при загрузке ERRxx (0xd5)",\
			   0xe0: "Ошибка связи с купюроприемником (0xe0)",\
			   0xe1: "Купюроприемник занят (0xe1)",\
                           0xe2: "Итог чека не соответствует итогу купюроприемника (0xe2)",\
			   0xe3: "Ошибка купюроприемника (0xe3)",\
                           0xe4: "Итог купюроприемника не нулевой (0xe4)"\
                        }[value]

        def __str__(self):
            return self.s

        def __unicode__(self):
            return unicode(str(self.s),'utf8')
#commands
class KKM:
        def __init__(self,conn,password=DEFAULT_PASSWORD):
                self.conn     = conn
                self.password = password
                if self.conn.isOpen:
                    print('conn ok')
                    
                if self.__checkState()!=NAK:
                        buffer=''
                        while self.conn.inWaiting():
                                buffer += self.conn.read()
                        self.conn.write(ACK+ENQ)
                        if self.conn.read(1)!=NAK:
                                raise RuntimeError("NAK expected")

        def __checkState(self):
                """Проверить на готовность"""
                if self.conn.isOpen:
                    print('check conn ok')
                self.conn.write(ENQ)
                repl = self.conn.read(1)
                print('repl='+repl)
                if not self.conn.isOpen():
                        raise RuntimeError("Serial port closed unexpectly")
                if repl==NAK:
                        return NAK
                if repl==ACK:
                        return ACK
                raise RuntimeError("Unknown answer")

        def __clearAnswer(self):
                """Сбросить ответ если он болтается в ККМ"""
                def oneRound():
                        self.conn.flush()
                        time.sleep(MIN_TIMEOUT*10)
                        self.conn.write(ENQ)
                        a = self.conn.read(1)
                        time.sleep(MIN_TIMEOUT*2)
                        if a==NAK:
                                return 1
                        elif a==ACK:
                                a = self.conn.read(1)
                                time.sleep(MIN_TIMEOUT*2)
                                if a!=STX:
                                        raise RuntimeError("Something wrong")
                                length = ord(self.conn.read(1))
                                time.sleep(MIN_TIMEOUT*2)
                                data = self.conn.read(length+1)
                                self.conn.write(ACK)
                                time.sleep(MIN_TIMEOUT*2)
                                return 2
                        else:
                                raise RuntimeError("Something wrong")
                n=0
                while n<MAX_TRIES and oneRound()!=1:
                        n+=1
                if n>=MAX_TRIES:
                        return 1
                return 0

        def __readAnswer(self):
                """Считать ответ ККМ"""
                a = self.conn.read(1)
                if a==ACK:
                        a = self.conn.read(1)
                        if a==STX:
                         length   = ord(self.conn.read(1))
                         cmd      = self.conn.read(1)
                         errcode  = self.conn.read(1)
                         data     = self.conn.read(length-2)
                         if length-2!=len(data):
                            #print hexStr(data)
                              self.conn.write(NAK)
                              raise RuntimeError("Length (%i) not equal length of data (%i)" % (length, len(data)))
                         rcrc   = self.conn.read(1)
                         mycrc = LRC(chr(length)+cmd+errcode+data)
                         if rcrc!=mycrc:
                                    self.conn.write(NAK)
                                    raise RuntimeError("Wrong crc %i must be %i " % (mycrc,ord(rcrc)))
                         self.conn.write(ACK)
                         self.conn.flush()
                         time.sleep(MIN_TIMEOUT*2)
                         if ord(errcode)!=0:
                                #print('errcode nvg='+str(ord(errcode)))
                                raise kkmException(ord(errcode))
                         return {'cmd':cmd,'errcode':ord(errcode),'data':data}
                        else:
                                raise RuntimeError("a!=STX %s %s" % (hex(ord(a)),hex(ord(STX))))
                elif a==NAK:
                        return None
                else:
                        raise RuntimeError("a!=ACK %s %s" % (hex(ord(a)),hex(ord(ACK))))



        def __sendCommand(self,cmd,params):
                """Стандартная обработка команды"""
                self.conn.flush()
                data   = chr(cmd)+params
                length = 1+len(params)
                content = chr(length)+data
                crc = LRC(content)
                self.conn.write(STX+content+crc)
                self.conn.flush()
                return OK
        
        def open(self):
                """Open"""
                self.__clearAnswer()
                self.__sendCommand(0x13,self.password)
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                print('errcode='+str(a['errcode']))
                return a['errcode']

        def Beep(self):
                """Гудок"""
                self.__clearAnswer()
                self.__sendCommand(0x13,self.password)
                answer = self.__readAnswer()
                return answer['errcode']

        def shortStatusRequest(self):
                """Request short status info"""
                self.__clearAnswer()
                self.__sendCommand(0x10,self.password)
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                self.LAST_ERROR = errcode
                ba = byte2array(ord(data[2]))
                ba.extend(byte2array(ord(data[1])))
                dbg("ba=",ba)
                result = {
                                  'operator':                  ord(data[0]), \
                                  'flags':                     data[1]+data[2], \
                                  'mode':                      ord(data[3]),\
                                  'submode':                   ord(data[4]),\
                                  'rull_oper_log':             ba[0],\
                                  'rull_check_log':            ba[1],\
                                  'upper_sensor_skid_document':ba[2],\
                                  'lower_sensor_skid_document':ba[3],\
                                  '2decimal_digits':           ba[4],\
                                  'eklz':                      ba[5],\
                                  'optical_sensor_oper_log':   ba[6],\
                                  'optical_sensor_chek_log':   ba[7],\
                                  'thermo_oper_log':           ba[8],\
                                  'thermo_check_log':          ba[9],\
                                  'box_open':                  ba[10],\
                                  'money_box':                 ba[11],\
                                  'eklz_full':                 ba[14],\
                                  'battaryvoltage':            ord(data[6]),\
                                  'powervoltage':              ord(data[7]),\
                                  'errcodefp':                 ord(data[8]),\
                                  'errcodeeklz':               ord(data[9]),\
                                  'rezerv':                    data[10:] }
                return result

        def statusRequest(self):
                """Request status info"""
                self.__clearAnswer()
                self.__sendCommand(0x11,self.password)
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                print "data len = ",len(data)
                ba = byte2array(ord(data[12]))
                ba.extend(byte2array(ord(data[11])))
                dbg('len of data',len(data))
                result = {'errcode':                   errcode, \
                          'operator':                  ord(data[0]), \
                          'fr_ver':                    data[1]+data[2],\
                          'fr_build':                  unpack('i',data[3]+data[4]+chr(0x0)+chr(0x0))[0],\
                          'fr_date':                   '%02i.%02i.20%02i' % (ord(data[5]),ord(data[6]),ord(data[7])),\
                          'zal_num':                   ord(data[8]),\
                          'doc_num':                   unpack('i',data[9]+data[10]+chr(0x0)+chr(0x0))[0],\
                          'fr_flags':                  unpack('i',data[11]+data[12]+chr(0x0)+chr(0x0))[0],\
                          'mode':                      ord(data[13]),\
                          'submode':                   ord(data[14]),\
                          'fr_port':                   ord(data[15]),\
                          'fp_ver':                    data[16]+data[17],\
                          'fp_build':                  unpack('i',data[18]+data[19]+chr(0x0)+chr(0x0))[0],\
                          'fp_datep':                  '%02i.%02i.20%02i' % (ord(data[20]),ord(data[21]),ord(data[22])),\
                          'date':                      '%02i.%02i.20%02i' % (ord(data[23]),ord(data[24]),ord(data[25])),\
                          'time':                      '%02i:%02i:%02i' % (ord(data[26]),ord(data[27]),ord(data[28])),\
                          'flags_fp':                  ord(data[29]),\
                          'factory_number':            unpack('i',data[30]+data[31]+data[32]+data[33])[0],\
                          'last_closed_tour':          unpack('i',data[34]+data[35]+chr(0x0)+chr(0x0))[0],\
                          'free_fp_records':           data[36]+data[37],\
                          'reregister_count':          data[38],\
                          'reregister_count_left':     ord(data[39]),\
                          'INN':data[40]+data[41]+data[42]+data[43]+data[44]+data[45],\
                          'rull_oper_log':             ba[0],\
                          'rull_check_log':            ba[1],\
                          'upper_sensor_skid_document':ba[2],\
                          'lower_sensor_skid_document':ba[3],\
                          '2decimal_digits':           ba[4],\
                          'eklz':                      ba[5],\
                          'optical_sensor_oper_log':   ba[6],\
                          'optical_sensor_chek_log':   ba[7],\
                          'thermo_oper_log':           ba[8],\
                          'thermo_check_log':          ba[9],\
                          'box_open':                  ba[10],\
                          'money_box':                 ba[11],\
                          'eklz_full':                 ba[14]}
                return result

        def cashIncome(self,count):
                """Внесение денег"""
                self.__clearAnswer()
                bin_summ = pack('l',float2100int(count)).ljust(5,chr(0x0))
                self.__sendCommand(0x50,self.password+bin_summ)
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                self.DOC_NUM    = unpack('i',data[0]+data[1]+chr(0x0)+chr(0x0))[0]


        def cashOutcome(self,count):
                """Выплата денег"""
                self.__clearAnswer()
                bin_summ = pack('l',float2100int(count)).ljust(5,chr(0x0))
                self.__sendCommand(0x51,self.password+bin_summ)
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                self.OP_CODE    = ord(data[0])
                self.DOC_NUM    = unpack('i',data[1]+data[2]+chr(0x0)+chr(0x0))[0]

        def openCheck(self,ctype):
            """Команда:     8DH. Длина сообщения: 6 байт.
                     • Пароль оператора (4 байта)
                     • Тип документа (1 байт): 0 – продажа;
                                               1 – покупка;
                                               2 – возврат продажи;
                                               3 – возврат покупки
                Ответ:       8DH. Длина сообщения: 3 байта.
                     • Код ошибки (1 байт)
                     • Порядковый номер оператора (1 байт) 1...30
            """
            self.__clearAnswer()
            if ctype not in range(0,4):
                   raise RuntimeError("Check type may be only 0,1,2,3 value")
            self.__sendCommand(0x8D,self.password+chr(ctype))
            a = self.__readAnswer()
            cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
            self.OP_CODE    = ord(data[0])
            return errcode


        def Sale(self,count,price,text=u"",department=1,taxes=[0,0,0,0][:]):
            """Продажа
                Команда:     80H. Длина сообщения: 60 байт.
                     • Пароль оператора (4 байта)
                     • Количество (5 байт) 0000000000...9999999999
                     • Цена (5 байт) 0000000000...9999999999
                     • Номер отдела (1 байт) 0...16
                     • Налог 1 (1 байт) «0» – нет, «1»...«4» – налоговая группа
                     • Налог 2 (1 байт) «0» – нет, «1»...«4» – налоговая группа
                     • Налог 3 (1 байт) «0» – нет, «1»...«4» – налоговая группа
                     • Налог 4 (1 байт) «0» – нет, «1»...«4» – налоговая группа
                     • Текст (40 байт)
                Ответ:       80H. Длина сообщения: 3 байта.
                     • Код ошибки (1 байт)
                     • Порядковый номер оператора (1 байт) 1...30
            """
            self.__clearAnswer()
            if count < 0 or count > 9999999999:
                   raise RuntimeError("Count myst be in range 0..9999999999")
            if price <0 or price > 9999999999:
                   raise RuntimeError("Price myst be in range 0..9999999999")
            if not department in range(0,17):
                   raise RuntimeError("Department myst be in range 1..16")
            if len(text)>40:
                   raise RuntimeError("Text myst be less than 40 chars")
            if len(taxes)!=4:
                   raise RuntimeError("Count of taxes myst be 4")
            for t in taxes:
                if t not in range(0,4):
                   raise RuntimeError("taxes myst be only 0,1,2,3,4")
            bcount = pack('l',float2100int(count)*10)+chr(0x0)
            bprice = pack('l',float2100int(price))+chr(0x0) #если сразу * 100 то ошибка округления
            bdep   = chr(department)
            btaxes = "%s%s%s%s" % tuple(map(lambda x: chr(x), taxes))
            print 'taxes = ',taxes,'bin=',hexStr(btaxes)
            btext  = text.encode('cp1251').ljust(40,chr(0x0))
#            time.sleep(0.5)
            self.__sendCommand(0x80,self.password+bcount+bprice+bdep+btaxes+btext)
#            time.sleep(1)
            a = self.__readAnswer()
#            time.sleep(0.5)
            cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
            self.OP_CODE    = ord(data[0])
            return errcode

        def returnSale(self,count,price,text=u"",department=1,taxes=[0,0,0,0][:]):
            """Возврат продажи
                Команда:     82H. Длина сообщения: 60 байт.
                     • Пароль оператора (4 байта)
                     • Количество (5 байт) 0000000000...9999999999
                     • Цена (5 байт) 0000000000...9999999999
                     • Номер отдела (1 байт) 0...16
                     • Налог 1 (1 байт) «0» – нет, «1»...«4» – налоговая группа
                     • Налог 2 (1 байт) «0» – нет, «1»...«4» – налоговая группа
                     • Налог 3 (1 байт) «0» – нет, «1»...«4» – налоговая группа
                     • Налог 4 (1 байт) «0» – нет, «1»...«4» – налоговая группа
                     • Текст (40 байт)
                Ответ:       80H. Длина сообщения: 3 байта.
                     • Код ошибки (1 байт)
                     • Порядковый номер оператора (1 байт) 1...30
            """
            self.__clearAnswer()
            if float2100int(count)*10 < 0 or float2100int(count)*10 > 9999999999:
                   raise RuntimeError("Count myst be in range 0..9999999999")
            if float2100int(price) <0 or float2100int(price) > 9999999999:
                   raise RuntimeError("Price myst be in range 0..9999999999")
            if not department in range(0,17):
                   raise RuntimeError("Department myst be in range 1..16")
            if len(text)>40:
                   raise RuntimeError("Text myst be less than 40 chars")
            if len(taxes)!=4:
                   raise RuntimeError("Count of taxes myst be 4")
            for t in taxes:
                if t not in range(0,4):
                   raise RuntimeError("taxes myst be only 0,1,2,3,4")
            bcount = pack('l',float2100int(count)*10)+chr(0x0)
            bprice = pack('l',float2100int(price))+chr(0x0)
            bdep   = chr(department)
            btaxes = "%s%s%s%s" % tuple(map(lambda x: chr(x), taxes))
            btext  = text.encode('cp1251').ljust(40,chr(0x0))
            self.__sendCommand(0x82,self.password+bcount+bprice+bdep+btaxes+btext)
#            time.sleep(0.8)
            a = self.__readAnswer()
            cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
            self.OP_CODE    = ord(data[0])
            return errcode

        def closeCheck(self,summa,text=u"",summa2=0,summa3=0,summa4=0,sale=0,taxes=[0,0,0,0][:]):
            """
                Команда:     85H. Длина сообщения: 71 байт.
                     • Пароль оператора (4 байта)
                     • Сумма наличных (5 байт) 0000000000...9999999999
                     • Сумма типа оплаты 2 (5 байт) 0000000000...9999999999
                     • Сумма типа оплаты 3 (5 байт) 0000000000...9999999999
                     • Сумма типа оплаты 4 (5 байт) 0000000000...9999999999
                     • Скидка/Надбавка(в случае отрицательного значения) в % на чек от 0 до 99,99
                       % (2 байта со знаком) -9999...9999
                     • Налог 1 (1 байт) «0» – нет, «1»...«4» – налоговая группа
                     • Налог 2 (1 байт) «0» – нет, «1»...«4» – налоговая группа
                     • Налог 3 (1 байт) «0» – нет, «1»...«4» – налоговая группа
                     • Налог 4 (1 байт) «0» – нет, «1»...«4» – налоговая группа
                     • Текст (40 байт)
                Ответ:       85H. Длина сообщения: 8 байт.
                     • Код ошибки (1 байт)
                     • Порядковый номер оператора (1 байт) 1...30
                     • Сдача (5 байт) 0000000000...9999999999
            """
            self.__clearAnswer()
            if float2100int(summa) <0 or float2100int(summa) > 9999999999:
                   raise RuntimeError("Summa myst be in range 0..9999999999")
            if float2100int(summa2) <0 or float2100int(summa2) > 9999999999:
                   raise RuntimeError("Summa2 myst be in range 0..9999999999")
            if float2100int(summa3) <0 or float2100int(summa3) > 9999999999:
                   raise RuntimeError("Summa3 myst be in range 0..9999999999")
            if float2100int(summa4) <0 or float2100int(summa4) > 9999999999:
                   raise RuntimeError("Summa4 myst be in range 0..9999999999")
            if float2100int(sale) <-9999 or float2100int(sale) > 9999:
                   raise RuntimeError("Sale myst be in range -9999..9999")
            if len(text)>40:
                   raise RuntimeError("Text myst be less than 40 chars")
            if len(taxes)!=4:
                   raise RuntimeError("Count of taxes myst be 4")
            for t in taxes:
                if t not in range(0,4):
                   raise RuntimeError("taxes myst be only 0,1,2,3,4")

            bsumma  = pack('l',float2100int(summa))+chr(0x0)
            bsumma2 = pack('l',float2100int(summa2))+chr(0x0)
            bsumma3 = pack('l',float2100int(summa3))+chr(0x0)
            bsumma4 = pack('l',float2100int(summa4))+chr(0x0)
            bsale   = pack('h',float2100int(sale))
            btaxes = "%s%s%s%s" % tuple(map(lambda x: chr(x), taxes))
            btext  = text.encode('cp1251').ljust(40,chr(0x0))
            self.__sendCommand(0x85,self.password+bsumma+bsumma2+bsumma3+bsumma4+bsale+btaxes+btext)
            a = self.__readAnswer()
            cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
            self.OP_CODE    = ord(data[0])
            #Сдачу я не считаю....
            time.sleep(0.5) # Тут не успевает иногда
            return errcode

        def reportWoClose(self,admpass):
                """Отчет без гашения"""
                self.__clearAnswer()
                self.__sendCommand(0x40,admpass)
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                self.OP_CODE    = ord(data[0])
                return errcode

        def reportWClose(self,admpass):
                """Отчет с гашением"""
                self.__clearAnswer()
                self.__sendCommand(0x41,admpass)
                #self.__sendCommand(0x27,admpass)
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                self.OP_CODE    = ord(data[0])
                return errcode

        def cutCheck(self,cutType):
                """Отрезка чека
                   Команда:     25H. Длина сообщения: 6 байт.
                        • Пароль оператора (4 байта)
                        • Тип отрезки (1 байт) «0» – полная, «1» – неполная
                   Ответ:       25H. Длина сообщения: 3 байта.
                        • Код ошибки (1 байт)
                        • Порядковый номер оператора (1 байт) 1...30
                """
                self.__clearAnswer()
                if cutType!=0 and cutType!=1:
                   raise RuntimeError("cutType myst be only 0 or 1 ")
                self.__sendCommand(0x25,self.password+chr(cutType))
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                self.OP_CODE    = ord(data[0])
                return errcode

        def continuePrint(self):
                """Продолжение печати
                Команда:    B0H. Длина сообщения: 5 байт.
                        • Пароль оператора, администратора или системного администратора (4 байта)
                   Ответ:      B0H. Длина сообщения: 3 байта.
                        • Код ошибки (1 байт)
                        • Порядковый номер оператора (1 байт) 1...30
                """
                self.__clearAnswer()
                self.__sendCommand(0xB0,self.password)
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                self.OP_CODE    = ord(data[0])
                return errcode

        def repeatDoc(self):
                """Команда:    8CH. Длина сообщения: 5 байт.
                     • Пароль оператора (4 байта)
                Ответ:      8CH. Длина сообщения: 3 байта.
                     • Код ошибки (1 байт)
                     • Порядковый номер оператора (1 байт) 1...30
                     Команда выводит на печать копию последнего закрытого документа
                                 продажи, покупки, возврата продажи и возврата покупки.
                """
                self.__clearAnswer()
                self.__sendCommand(0x8C,self.password)
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                self.OP_CODE    = ord(data[0])
                return errcode

        def cancelCheck(self):
                """Команда:    88H. Длина сообщения: 5 байт.
                     • Пароль оператора (4 байта)
                Ответ:      88H. Длина сообщения: 3 байта.
                     • Код ошибки (1 байт)
                     • Порядковый номер оператора (1 байт) 1...30
                """
                self.__clearAnswer()
                self.__sendCommand(0x88,self.password)
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                self.OP_CODE    = ord(data[0])
                return errcode

        def setDate(self,admpass,day,month,year):
                """Установка даты
                Команда:     22H. Длина сообщения: 8 байт.
                     • Пароль системного администратора (4 байта)
                     • Дата (3 байта) ДД-ММ-ГГ
                Ответ:       22H. Длина сообщения: 2 байта.
                     • Код ошибки (1 байт)
                """
                self.__clearAnswer()
                self.__sendCommand(0x22,admpass+chr(day)+chr(month)+chr(year-2000))
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                return errcode

        def acceptSetDate(self,admpass,day,month,year):
                """Установка даты (бред какой-то)
                Команда:     23H. Длина сообщения: 8 байт.
                     • Пароль системного администратора (4 байта)
                     • Дата (3 байта) ДД-ММ-ГГ
                Ответ:       23H. Длина сообщения: 2 байта.
                     • Код ошибки (1 байт)
                """
                self.__clearAnswer()
                self.__sendCommand(0x23,admpass+chr(day)+chr(month)+chr(year-2000))
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                return errcode

        def setTime(self,admpass,hour,minutes,secs):
                """Установка даты
                Команда:    21H. Длина сообщения: 8 байт.
                             • Пароль системного администратора (4 байта)
                             • Время (3 байта) ЧЧ-ММ-СС
                        Ответ:      21H. Длина сообщения: 2 байта.
                             • Код ошибки (1 байт)
                """
                self.__clearAnswer()
                self.__sendCommand(0x21,admpass+chr(hour)+chr(minutes)+chr(secs))
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                return errcode



        def setTableValue(self,admpass,table,row,field,value):
                """Записать значение в таблицу, ряд, поле
                поля бывают бинарные и строковые, поэтому value
                делаем в исходном виде
                """
                self.__clearAnswer()
                drow    = pack('l',row).ljust(2,chr(0x0))[:2]
                self.__sendCommand(0x1e,admpass+chr(table)+drow+chr(field)+value)
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                return errcode
        def printString(self,check_ribbon=True,control_ribbon=True,text=u""):
                """Печать строки без ограничения на 40 символов"""
                t = text
                while len(t)>0:
                        self._printString(check_ribbon=check_ribbon,control_ribbon=check_ribbon,text=t[:39])
                        t = t[39:]
        def _printString(self,check_ribbon=True,control_ribbon=True,text=u""):
                """Напечатать строку"""
                self.__clearAnswer()
                flag = 0
                if check_ribbon:
                        flag = flag | 1
                if control_ribbon:
                        flag = flag | 2
                if len(text)>40:
                        raise RuntimeError("Length of string myst be less or equal 40 chars")
                s = text.encode('cp1251').ljust(40,chr(0x0))
#                time.sleep(0.2)
                self.__sendCommand(0x17,self.password+bufStr(flag)+s)
#                time.sleep(0.5)
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                self.OP_CODE    = ord(data[0])
                return errcode

        def Run(self,check_ribbon=True,control_ribbon=True,doc_ribbon=False,row_count=1):
                """Прогон"""
                self.__clearAnswer()
                flag = 0
                if check_ribbon:
                        flag = flag | 1
                if control_ribbon:
                        flag = flag | 2
                if doc_ribbon:
                        flag = flag | 4
                if row_count not in range(1,255):
                        raise RuntimeError("Line count myst be in 1..255 range")

                self.__sendCommand(0x29,self.password+bufStr(flag,row_count))
                a = self.__readAnswer()
                cmd,errcode,data = (a['cmd'],a['errcode'],a['data'])
                self.OP_CODE    = ord(data[0])
                return errcode

class ShtrihFRKDummy:
        def __init__(self,password,admin_password,connection):
                self.password   = password
                self.admin_password = admin_password
                self.connection = connection

        def open(self):
                """Открыть работу с ККМ"""
                pass

        def getStatusString(self):
                """Вернет строку описывающую режим и состояние ККМ"""
                return 'Dummy state'

        def printCheck(self,header,summ,comment,buyer,ctype=0,nds=0):
                """Напечатать чек.
                        с суммой summ
                        с комментарием comment
                        c покупателем buyer
                        тип 0 платеж 1 возврат
                        nds = 0 без nds все остальное - размер НДС
                """
                pass

        def printCopy(self):
                """Напечатать копию последнего документа"""
                pass
        def closeSession(self,password=None):
                """Закрыть смену с печатью отчета"""
                pass
        def printReport(self,password=None):
                """Печать отчета"""
                pass
        def continuePrint(self):
                """Продолжить печать прерванную из-за сбоя"""
                pass
        def cancelCheck(self):
                """Отменить операцию"""
                pass
        def setupDateTime(self,password):
                """Установить время и дату как в компьютере"""
                pass

        def inputMoney(self,summ):
                """Внести деньги в кассу"""
                pass

        def outputMoney(self,summ):
                """Инкасировать"""
                pass

        def cutRibbon(self):
                """Обрезать ленту"""
                pass


class ShtrihFRK(ShtrihFRKDummy):
        def __init__(self,password,admin_password,connection):
                ShtrihFRKDummy.__init__(self,password,admin_password,connection)
                self.kkm=KKM(self.connection,password=self.password)

        def open(self):
                """Открыть работу с ККМ"""
                pass

        def getStatusString(self):
                """Вернет строку описывающую режим и состояние ККМ"""
                srq = self.kkm.statusRequest()
                s = ''
                s +=  ' Режим: %s' % FP_MODES_DESCR.get(srq['mode'],' Режим неизвестен')
                s +=  ' Подрежим: %s' % FR_SUBMODES_DESCR.get(srq['mode'],{}).get(srq['submode'],' Подрежим неизвестен')
                if srq['errcode']==0: s+=' Без ошибок'
                else:                      s+=' Ошибка %s' % hex(srq['errcode'])
                return s

        def printCheck(self,header,summ,comment,buyer,ctype=0,nds=0):
                """Напечатать чек.
                        с суммой summ
                        с комментарием comment
                        c покупателем buyer
                        тип 0 платеж 1 возврат
                        nds = 0 без nds все остальное - размер НДС
                """
                if nds>0:
                        #Включаем начисление налогов на ВСЮ операцию чека
                        self.kkm.setTableValue(self.admin_password,1,1,17,chr(0x1))
                        #Включаем печатать налоговые ставки и сумму налога
                        self.kkm.setTableValue(self.admin_password,1,1,19,chr(0x2))
                        self.kkm.setTableValue(self.admin_password,6,2,1,pack('l',nds*100)[:2])

                self.kkm.openCheck(ctype*2)
                taxes = [0,0,0,0]
                for l in header.split('\n'):
                        self.kkm.printString(l)
                if ctype==0:
                        self.kkm.printString(u"Принято от: %s" + buyer)
                        if nds>0:
                                taxes[0]=2
                        self.kkm.Sale(1,summ,text=comment,taxes=taxes)
                else:
                        if nds>0:
                                taxes[3]=2
                        self.kkm.printString(u"Возвращено: %s" % buyer)
                        taxes = [0,0,0,0]
                        self.kkm.returnSale(1,summ,text=comment,taxes=taxes)
                if nds>0:
                   taxes[0]=2
                self.kkm.closeCheck(summ,u"------------------",taxes)
		self.kkm.printString(comment)

        def printCopy(self):
                """Напечатать копию последнего документа"""
                pass
        def closeSession(self,password=None):
                """Закрыть смену с печатью отчета"""
                if not password:
                        password = self.password
                self.kkm.reportWClose(password)
        def printReport(self,password=None):
                """Печать отчета"""
                if not password:
                        password = self.password
                self.kkm.reportWoClose(password)
        def continuePrint(self):
                """Продолжить печать прерванную из-за сбоя"""
                self.kkm.continuePrint()
        def cancelCheck(self):
                """Отменить операцию"""
                self.kkm.cancelCheck()
        def setupDateTime(self,password):
                """Установить время и дату как в компьютере"""
                t = time.localtime()
                self.kkm.setDate(password,t.tm_mday,t.tm_mon,t.tm_year)
                self.kkm.acceptSetDate(password,t.tm_mday,t.tm_mon,t.tm_year)
                t = time.localtime()
                self.kkm.setTime(password,t.tm_hour,t.tm_min,t.tm_sec)

        def inputMoney(self,summ):
                """Внести деньги в кассу"""
                self.kkm.cashIncome(summ)

        def outputMoney(self,summ):
                """Инкасировать"""
                self.kkm.cashOutcome(summ)

        def cutRibbon(self):
                """Обрезать ленту"""
                self.kkm.cutCheck(0)

if __name__=="__main__":
        import time
        ser = serial.Serial(PORT, 4800,\
                            parity=serial.PARITY_NONE,\
                            stopbits=serial.STOPBITS_ONE,\
                            timeout=0.7,\
                            writeTimeout=0.7)
        print('connected')
#
        sfrk = ShtrihFRK(DEFAULT_PASSWORD,DEFAULT_ADM_PASSWORD,ser)
#
        sfrk.printCheck(u"Тестовый\nзаголовок",123.33,u'Бентли',u'Тонконогов',ctype=0,nds=0)
#
#        sfrk.printCheck(u"Тестовый\nзаголовок",123.33,u'Лытыдыбр',u'Жанна Фриске',ctype=1,nds=0)
#
#        sfrk.printCheck(u"Тестовый\nзаголовок",100.00,u'Лытыдыбр',u'Жанна Фриске',ctype=0,nds=18)
#
#        sfrk.printCheck(u"Тестовый\nзаголовок",123.33,u'Лытыдыбр',u'Жанна Фриске',ctype=1,nds=18)
#
        #kkm = KKM(ser,password=DEFAULT_ADM_PASSWORD)
#        kkm.Sale(1,100,"qqqq",1,[1,0,0,0])
#
        #kkm.Beep()
#        kkm.open()
#        kkm.openCheck(0)
#        kkm.Beep()
#        time.sleep(1)
        #kkm.printString(True,True,u"Привет всем!")
        #kkm.cutCheck(0)
#        kkm.setTableValue(DEFAULT_ADM_PASSWORD,1,1,17,chr(0x1))
#
#        kkm.cashOutcome(123.11)
#
#        time.sleep(1)
#        kkm.setTableValue(DEFAULT_ADM_PASSWORD,1,1,17,chr(0x0))
        #print "WO",
        #kkm.reportWoClose(DEFAULT_ADM_PASSWORD)
        #print "Ok"
        #time.sleep(1)
#        print "W",
#        kkm.reportWClose(DEFAULT_ADM_PASSWORD)
#        print "Ok"

#        kkm.printString(True,True,u"Привет мир! Hello world")
#        kkm.Run(check_ribbon=True,control_ribbon=True,row_count=10)
#
#        time.sleep(1)
#        st = kkm.statusRequest()
#        for k,v in st.items():
#                print k,":\t\t",v
#        kkm.TestRun()
        ser.close()

