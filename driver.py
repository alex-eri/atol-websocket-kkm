#!/usr/bin/python
# -*- coding:utf-8 -*-

import json
import os
import signal
import sys
import time
from multiprocessing import Queue
from threading import Thread

import serial

import dto9fptr
from websocket_server import WebsocketServer

if sys.version[0] == '2':
    reload(sys)
#pylint: disable-msg=E1101
    sys.setdefaultencoding("utf-8")

driver = dto9fptr.Fptr('./fptr/libfptr.so', 15)

queue = Queue()
exit = False

class EFptrException(Exception):
    pass

class Runner(Thread):
    def run(self):
        a = 0
        while not exit:
            a = a + 1
            if a > 50:
                driver.GetCurrentStatus()
                errorCheck(True)
                a = 0
            if queue.qsize() > 0:
                job = queue.get()
                for i in server.clients:
                    if i['id'] == job['client']:
                        processMessage(i, server, job['message'])
            else:
                time.sleep(0.1)

def errorCheck(exitIfFail = False):
    global exit
    if driver.get_ResultCode() != 0:
        if (exitIfFail):
            try:
                try:
                    server.server_close()
                finally:
                    exit = True
                    sys.exit()
            except:
                pass
        else:
            raise EFptrException(driver.get_ResultDescription())

def setTableValue(table, row, field, type, value):
    driver.put_Table(table)
    driver.put_Row(row)
    driver.put_Field(field)
    driver.put_FieldType(0)
    driver.put_Caption(value)
    driver.SetTableField()
    errorCheck()

def setFiscalProperty(property, type, value, checkForError = True):
    driver.put_FiscalPropertyNumber(property) 
    driver.put_FiscalPropertyPrint(1) 
    driver.put_FiscalPropertyType(type) 
    driver.put_FiscalPropertyValue(value) 
    driver.WriteFiscalProperty()
    if checkForError:
        errorCheck()

def setMode(mode):
    driver.put_Mode(mode)
    driver.put_UserPassword(30)
    driver.SetMode()
    errorCheck()

def font(f):
    setMode(4)
    setTableValue(2, 1, 32, 0, f)

def fptrInit():
    driver.put_DeviceSingleSetting('Model', 57)
    driver.put_DeviceSingleSetting('UserPassword', 30)
    driver.put_DeviceSingleSetting('Port', 'USB$' + sys.argv[1])
    driver.put_DeviceSingleSetting('Protocol', 2)
    driver.put_DeviceSingleSetting('SearchDir', './fptr')
    driver.ApplySingleSettings()
    errorCheck()
    driver.put_DeviceEnabled(True)
    errorCheck()
    driver.CancelCheck()
    # Режим программирования
    # на ошибки не проверяем, если, например, чек открыт то они будут
    setMode(4)
    # Отключаем печать способа и признака расчета в позициях (116 и 117)
    setTableValue(2, 1, 116, 0, '0')
    setTableValue(2, 1, 117, 0, '0')
    # Шаблон чека №1
    setTableValue(2, 1, 111, 0, '1')
    # Яркость печати
    setTableValue(2, 1, 19, 0, '13')
    # Отключаем печать названия секции
    setTableValue(2, 1, 15, 0, '0')
    # Шрифт
    font(3)
    # Все норм, бибикаем
    beep()

def aReport(mode, type):
    setMode(mode)
    driver.put_ReportType(type)
    driver.Report()
    errorCheck()
    driver.GetCurrentStatus()
    errorCheck()

def check(data):
    # Режим регистрации
    setMode(1)
    # Картинка из памяти
    #driver.put_PictureNumber(2)
    #driver.put_LeftMargin(120)
    #driver.PrintPictureByNumber()
    #errorCheck()
    # Имя и должность кассира
    if (data['cashier']):
        setFiscalProperty(1021, 5, data['cashier'])
    # Метод выполняет GetStatus(), SetMode(), CancelCheck() см. руководство программиста
    driver.NewDocument()
    errorCheck()
    # Тип чека
    driver.put_CheckType(data['check_type'])
    # Открытие чека
    driver.OpenCheck()
    errorCheck()
    # Имя и должность кассира
    if (data['cashier']):
        setFiscalProperty(1021, 5, data['cashier'])
    # Email или телефон покупателя (ОФД отправит электронный чек)
    if (data['report']):
        setFiscalProperty(1008, 5, data['report'])
    # Позици чека
    for p in data['positions']:
        # Наименование товара
        driver.put_Name(p['name'])
        # Цена товара
        driver.put_Price(p['price'])
        # Количество товара
        driver.put_Quantity(p['quantity'])
        # Налог
        driver.put_TaxNumber(p['tax'])
        # Сумма строки (позиции)
        driver.put_PositionSum(p['sum'])
        # Предмет расчета 
        driver.put_PositionType(p['type'])
        # Способ расчета
        driver.put_PositionPaymentType(p['payment'])
        # Регистрация позиции
        driver.Registration()
        errorCheck()
    # Тип оплаты
    driver.put_TypeClose(data['payment_type'])
    # Сумма оплаты
    driver.put_Summ(data['sum'])
    # Регистрация платежа
    driver.Payment()
    errorCheck()
    # Закрытие чека.
    driver.CloseCheck()
    errorCheck()
    # Дата/Время последнего чека, тип чека, номер ФД чека, сумма чека, ФП
    driver.put_RegisterNumber(51)
    driver.GetRegister()
    #fd = str(driver.get_DocNumber()).strip()
    fp = str(driver.get_Value()).strip()
    # Серийник ФН
    driver.put_RegisterNumber(47)
    driver.GetRegister()
    fn = str(driver.get_SerialNumber()).strip()

    driver.GetCurrentStatus()
    errorCheck()

    return str(fn).zfill(16) + ':' + str(fp).zfill(10)

def correction(data):
    # Режим регистрации
    setMode(1)
    driver.NewDocument()
    driver.put_CheckType(7)
    driver.put_PrintCheck(1)
    driver.OpenCheck()
    errorCheck()

    # Имя и должность кассира
    if (data['cashier']):
        setFiscalProperty(1021, 5, data['cashier'])

    driver.put_Name('Коррекция прихода')
    driver.put_Price(data['sum'])
    driver.put_Quantity(1)
    driver.put_PositionSum(data['sum'])

    # Тип коррекции: 0 - самостоятельно, 1 - по предписанию
    setFiscalProperty(1173, 1, data['type'], False)

    # Основание для коррекции
    # Составной тег

    driver.BeginFormFiscalProperty()

    # Добавление тега 1177 к составному тегу
    # Документ

    driver.put_FiscalPropertyNumber(1177)
    driver.put_FiscalPropertyType(5)
    driver.put_FiscalPropertyValue(data['document'])
    driver.AddFiscalProperty()

    # Добавление тега 1178 к составному тегу
    # время в UnixTime

    driver.put_FiscalPropertyNumber(1178)
    driver.put_FiscalPropertyType(4)
    driver.put_FiscalPropertyValue(data['unixtime'])
    driver.AddFiscalProperty()

    # Добавление тега 1179 к составному тегу
    # Номер документа

    driver.put_FiscalPropertyNumber(1179)
    driver.put_FiscalPropertyType(5)
    driver.put_FiscalPropertyValue(data['number'])
    driver.AddFiscalProperty()

    driver.EndFormFiscalProperty()

    # Запись тега 1174
    setFiscalProperty(1174, 0, driver.get_FiscalPropertyValue(), False)

    driver.put_TaxNumber(data['tax'])
    driver.Registration()
    errorCheck()

    driver.put_TypeClose(0)
    driver.put_Summ(data['sum'])
    driver.CloseCheck()
    errorCheck()

    driver.GetCurrentStatus()
    errorCheck()

def beep():
    driver.Beep()
    errorCheck()

def display(caption):
    if len(sys.argv) > 2:
        p = serial.Serial('/dev/' + sys.argv[2], 9600)
        try:
            # Инициализация PD2800 в режиме протокола EPSON
            p.write('\x1B\x3D\x02\x1B\x74\x06\x1B\x52\x00\x0C' + str(caption).encode('cp866'))
            p.flushOutput()
            p.close()
        except:
            pass

def processMessage(client, server, message):
    try:
        data = json.loads(message)

        if (data['method'] == 'ping'):
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'value': 'pong', 'opened': driver.get_SessionOpened() }))
            return

        if (data['method'] == 'check'):
            # Пробить чек
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'value': check(data['data']), 'opened': driver.get_SessionOpened() }))
            return

        if (data['method'] == 'correction'):
            # Пробить чек коррекции
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'value': correction(data['data']), 'opened': driver.get_SessionOpened() }))
            return

        if (data['method'] == 'report_z'):
            # Z-Отчет
            setFiscalProperty(1021, 5, data['cashier'])
            aReport(3, 1)
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'opened': driver.get_SessionOpened() }))
            return
            
        if (data['method'] == 'report_x'):
            # X-Отчет
            aReport(2, 2)
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'] }))
            return

        if (data['method'] == 'report_c'):
            # Отчет по кассирам
            aReport(2, 8)
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'] }))
            return

        if (data['method'] == 'open'):
            setMode(1)
            setFiscalProperty(1021, 5, data['cashier'])
            driver.OpenSession()
            errorCheck()
            driver.GetCurrentStatus()
            errorCheck()
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'opened': driver.get_SessionOpened() }))
            return

        if (data['method'] == 'cash_in'):
            setMode(1)
            driver.CancelCheck()
            setFiscalProperty(1021, 5, data['cashier'])
            driver.OpenSession()
            # на ошибки не проверяем, смена может быть уже открыта
            driver.put_Summ(data['cash'])
            driver.CashIncome()
            errorCheck()
            driver.GetCurrentStatus()
            errorCheck()
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'opened': driver.get_SessionOpened() }))
            return

        if (data['method'] == 'cash_out'):
            setMode(1)
            driver.CancelCheck()
            driver.put_Summ(data['cash'])
            driver.CashOutcome()
            errorCheck()
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'] }))
            return

        if (data['method'] == 'fn'):
            # Серийник ФН
            driver.put_RegisterNumber(47)
            driver.GetRegister()
            errorCheck()
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'value': str(driver.get_SerialNumber()).strip() }))
            return

        if (data['method'] == 'display'):
            # Вывести что-то на дисплей покупателя
            display(data['data'])
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'] }))
            return
            
        server.send_message(client, json.dumps({ 'result': 'ERR', 'method': data['method'], 'type': 'invalid', 'value': 'Unknown method' }))

    except Exception as e:
        server.send_message(client, json.dumps({ 'result': 'ERR', 'type': type(e).__name__, 'value': e.args[0] }))
    
def messageReceived(client, server, message):
    queue.put({ 'client': client['id'], 'message': message })

def serviceShutdown(signum, frame):
    global exit

    exit = True
    sys.exit()

try:
    signal.signal(signal.SIGTERM, serviceShutdown)
    signal.signal(signal.SIGINT, serviceShutdown)    

    fptrInit()

    # 2x20 - две строки по 20 символов
    display('****************************************')

    runner = Runner()
    runner.start()

    server = WebsocketServer(9111, '0.0.0.0')
    server.set_fn_message_received(messageReceived)

    server.run_forever()

except Exception as e:
    print(str(e))
    exit = True
    sys.exit()
