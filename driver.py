#!/usr/bin/python
# -*- coding:utf-8 -*-

import dto9fptr
import os
import json
import sys
from websocket_server import WebsocketServer

reload(sys)
sys.setdefaultencoding('utf8')

driver = dto9fptr.Fptr(r'./fptr/libfptr.so', 15)

class EFptrException(Exception):
    pass

def errorCheck():
    result_code = driver.get_ResultCode()
    result_description = driver.get_ResultDescription()
    if result_code != 0:
        raise EFptrException(result_description)

def setTableValue(table, row, field, type, value):
    driver.put_Table(table)
    driver.put_Row(row)
    driver.put_Field(field)
    driver.put_FieldType(0)
    driver.put_Caption(value)
    driver.SetTableField()
    errorCheck()

def setFiscalProperty(property, type, value):
    driver.put_FiscalPropertyNumber(property) 
    driver.put_FiscalPropertyPrint(1) 
    driver.put_FiscalPropertyType(type) 
    driver.put_FiscalPropertyValue(value) 
    driver.WriteFiscalProperty() 
    errorCheck()

def init():
    driver.put_DeviceSingleSetting('Model', 57)
    driver.put_DeviceSingleSetting('UserPassword', 30)
    driver.put_DeviceSingleSetting('Port', 'USB$' + sys.argv[1])
    driver.put_DeviceSingleSetting('BaudRate', 115200)
    driver.put_DeviceSingleSetting('Protocol', 0)
    driver.put_DeviceSingleSetting('SearchDir', './fptr')
    driver.ApplySingleSettings()
    driver.put_DeviceEnabled(True)
    errorCheck()
    driver.GetStatus()
    errorCheck()
    # Режим программирования
    driver.put_Mode(4)
    errorCheck()
    # Отключаем печать способа и признака расчета в позициях (116 и 117)
    setTableValue(2, 1, 116, 0, "0")
    setTableValue(2, 1, 117, 0, "0")
    # Шаблон чека №1
    setTableValue(2, 1, 111, 0, "1")
    # Шрифт в чеке
    setTableValue(2, 1, 32, 0, "2")
    # Яркость печати
    setTableValue(2, 1, 19, 0, "13")
    # Отключаем печать названия секции
    setTableValue(2, 1, 15, 0, "0")
    # Все норм
    #driver.put_PictureNumber(2)
    #driver.put_LeftMargin(120)
    #driver.PrintPictureByNumber()
    #errorCheck()
    print "online: " + driver.get_SerialNumber() + " " + driver.get_DeviceDescription()
    beep()

def xReport():
    driver.put_Mode(2)
    driver.put_UserPassword(30)
    driver.SetMode()
    errorCheck()
    driver.put_ReportType(2)
    driver.Report()
    errorCheck()

def zReport():
    driver.put_Mode(3)
    driver.put_UserPassword(30)
    driver.SetMode()
    errorCheck()
    driver.put_ReportType(1)
    driver.Report()
    errorCheck()

def simpleCheck(data):
    # Режим регистрации
    driver.put_Mode(1)
    driver.put_UserPassword(30)
    driver.SetMode()
    errorCheck()
    # Метод выполняет GetStatus(), SetMode(), CancelCheck() см. руководство программиста
    driver.NewDocument()
    errorCheck()
    # Тип чека
    driver.put_CheckType(data['check_type'])
    errorCheck()
    # Открытие чека
    driver.OpenCheck()
    errorCheck()
    # Имя и должность кассира
    setFiscalProperty(1021, 5, data['cashier'])
    # Email или телефон покупателя (ОФД отправит электронный чек) 
    setFiscalProperty(1008, 5, data['report'])
    # Позици чека
    for p in data['positions']:
        # Наименование товара
        driver.put_Name(p['name'])
        # Цена товара
        driver.put_Price(p['price'])
        # Количество товара
        driver.put_Quantity(p['quantity'])
        # Налог (Без НДС)
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
    # Прием оплаты
    # Тип оплаты
    driver.put_TypeClose(data['payment_type'])
    errorCheck()
    # Сумма оплаты
    driver.put_Summ(data['sum'])
    errorCheck()
    # Регистрация платежа
    driver.Payment()
    errorCheck()
    # Закрытие чека.
    driver.CloseCheck()
    errorCheck()
    # Получаем номер смены и номер чека
    driver.GetCurrentStatus()
    errorCheck()
    return str(driver.get_Session()) + '.' + str(driver.get_CheckNumber())

def beep():
    driver.Beep()
    errorCheck()

def messageReceived(client, server, message):
    try:
        data = json.loads(message)

        if (data['method'] == 'ping'):
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'value': 'pong' }))
            return

        if (data['method'] == 'status'):
            driver.GetCurrentStatus()
            if driver.get_ResultCode() != 0:
                try:
                    server.server_close()
                except:
                    pass
                finally:
                    sys.exit()
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'] }))
            return

        if (data['method'] == 'check'):
            check = simpleCheck(data['data'])
            errorCheck()
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'value': check }))
            return

        if (data['method'] == 'serial'):
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'value': driver.get_SerialNumber() }))
            return
            
        if (data['method'] == 'z'):
            zReport()
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'] }))
            return
            
        if (data['method'] == 'x'):
            xReport()
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'] }))
            return
            
        server.send_message(client, json.dumps({ 'result': 'ERR', 'method': data['method'], 'type': 'invalid', 'value': 'Unknown method' }))

    except Exception as e:
        server.send_message(client, json.dumps({ 'result': 'ERR', 'type': type(e).__name__, 'value': e.args[0] }))

try:
    init()

    server = WebsocketServer(9111)

    server.set_fn_message_received(messageReceived)
    server.run_forever()

except Exception as e:
    print(str(e))
    sys.exit()

