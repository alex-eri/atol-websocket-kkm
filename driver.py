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
    # Отключаем печать способа и признака рассчета в позициях (116 и 117)
    driver.put_Table(2)
    driver.put_Row(1)
    driver.put_Field(116)
    driver.put_FieldType(0)
    driver.put_Caption("0")
    driver.SetTableField()
    errorCheck()
    driver.put_Table(2)
    driver.put_Row(1)
    driver.put_Field(117)
    driver.put_FieldType(0)
    driver.put_Caption("0")
    driver.SetTableField()
    errorCheck()
    # Шаблон чека №1
    driver.put_Table(2)
    driver.put_Row(1)
    driver.put_Field(111)
    driver.put_FieldType(0)
    driver.put_Caption("1")
    driver.SetTableField()
    errorCheck()
    # Шрифт в чеке
    driver.put_Table(2)
    driver.put_Row(1)
    driver.put_Field(32)
    driver.put_FieldType(0)
    driver.put_Caption("2")
    driver.SetTableField()
    errorCheck()
    # Яркость печати
    driver.put_Table(2)
    driver.put_Row(1)
    driver.put_Field(19)
    driver.put_FieldType(0)
    driver.put_Caption("13")
    driver.SetTableField()
    errorCheck()
    # Отключаем печать названия секции
    driver.put_Table(2)
    driver.put_Row(1)
    driver.put_Field(15)
    driver.put_FieldType(0)
    driver.put_Caption("0")
    driver.SetTableField()
    errorCheck()
    # Все норм
    #driver.put_PictureNumber(2)
    #driver.put_LeftMargin(120)
    #driver.PrintPictureByNumber()
    #errorCheck()
    print "online: " + driver.get_SerialNumber() + " " + driver.get_DeviceDescription()
    beep()

def errorCheck():
    result_code = driver.get_ResultCode()
    result_description = driver.get_ResultDescription()
    if result_code != 0:
        raise EFptrException(result_description)

def zReport():
    driver.put_Mode(3)
    errorCheck()
    driver.SetMode()
    errorCheck()
    driver.put_ReportType(1)
    errorCheck()
    driver.Report()
    errorCheck()

def simpleCheck(data):
    # Режим регистрации
    driver.put_Mode(1)
    errorCheck()
    # Метод выполняет GetStatus(), SetMode(), CancelCheck() см. руководство программиста
    driver.NewDocument()
    errorCheck()
    # Тип чека - Продажа
    driver.put_CheckType(1)
    errorCheck()
    # Открытие чека
    driver.OpenCheck()
    errorCheck()
    # Имя и должность кассира 
    driver.put_FiscalPropertyNumber(1021) 
    driver.put_FiscalPropertyPrint(1) 
    driver.put_FiscalPropertyType(5) 
    driver.put_FiscalPropertyValue(data['cashier']) 
    driver.WriteFiscalProperty() 
    errorCheck()
    # Email или телефон покупателя (ОФД отправит электронный чек) 
    driver.put_FiscalPropertyNumber(1008) 
    driver.put_FiscalPropertyPrint(1) 
    driver.put_FiscalPropertyType(5) 
    driver.put_FiscalPropertyValue(data['report']) 
    driver.WriteFiscalProperty()
    errorCheck()
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
    driver.CancelCheck()
    errorCheck()
    return 99
    # Прием оплаты
    # Тип оплаты
    driver.put_TypeClose(data['type'])
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
    # Получаем номер чека
    result = driver.get_CheckNumber()
    errorCheck()
    # Все норм, возвращаем номер чека
    return result

def beep():
    driver.Beep()
    errorCheck()

def messageReceived(client, server, message):
    try:
        data = json.loads(message)

        if (data['method'] == 'ping'):
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'data': 'pong' }))
            return

        if (data['method'] == 'status'):
            driver.GetStatus()
            if driver.get_ResultCode() != 0:
                server.server_close()
                sys.exit()
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'] }))
            return

        if (data['method'] == 'check'):
            check = simpleCheck(data['check'])
            errorCheck()
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'check': check }))
            return

        if (data['method'] == 'serial'):
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'data': driver.get_SerialNumber() }))
            return
            
        if (data['method'] == 'z'):
            zReport()
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'] }))
            return
            
        server.send_message(client, json.dumps({ 'result': 'ERR', 'method': data['method'], 'type': 'invalid', 'data': 'Unknown method' }))

    except Exception as e:
        server.send_message(client, json.dumps({ 'result': 'ERR', 'type': type(e).__name__, 'data': e.args[0] }))

try:
    init()

    server = WebsocketServer(9111)

    server.set_fn_message_received(messageReceived)
    server.run_forever()

except Exception as e:
    print(str(e))
    sys.exit()

