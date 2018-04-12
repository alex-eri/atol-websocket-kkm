#!/usr/bin/python
# -*- coding:utf-8 -*-

import dto9fptr
import os
import json
import sys
import serial
from websocket_server import WebsocketServer

reload(sys)
sys.setdefaultencoding('utf8')

driver = dto9fptr.Fptr('./fptr/libfptr.so', 15)

rn = ''
sn = ''
fn = ''
dd = ''

class EFptrException(Exception):
    pass

def errorCheck(exitIfFail = False):
    if driver.get_ResultCode() != 0:
        if (exitIfFail):
            try:
                try:
                    server.server_close()
                finally:
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

def setFiscalProperty(property, type, value):
    driver.put_FiscalPropertyNumber(property) 
    driver.put_FiscalPropertyPrint(1) 
    driver.put_FiscalPropertyType(type) 
    driver.put_FiscalPropertyValue(value) 
    driver.WriteFiscalProperty() 
    errorCheck()

def setMode(mode):
    driver.put_Mode(mode)
    driver.put_UserPassword(30)
    driver.SetMode()
    errorCheck()

def init():
    global sn, rn, dd, fn

    driver.put_DeviceSingleSetting('Model', 57)
    driver.put_DeviceSingleSetting('UserPassword', 30)
    driver.put_DeviceSingleSetting('Port', 'USB$' + sys.argv[1])
    driver.put_DeviceSingleSetting('Protocol', 2)
    driver.put_DeviceSingleSetting('SearchDir', './fptr')
    driver.ApplySingleSettings()
    errorCheck()
    driver.put_DeviceEnabled(True)
    errorCheck()
    # Режим регистрации
    setMode(1)
    driver.GetStatus()
    errorCheck()
    sn = driver.get_SerialNumber().strip()
    dd = driver.get_DeviceDescription().strip()
    # Режим программирования
    setMode(4)
    # Отключаем печать способа и признака расчета в позициях (116 и 117)
    setTableValue(2, 1, 116, 0, '0')
    setTableValue(2, 1, 117, 0, '0')
    # Шаблон чека №1
    setTableValue(2, 1, 111, 0, '1')
    # Шрифт в чеке
    setTableValue(2, 1, 32, 0, '2')
    # Яркость печати
    setTableValue(2, 1, 19, 0, '13')
    # Отключаем печать названия секции
    setTableValue(2, 1, 15, 0, '0')
    # Получаем РН фискальника
    driver.put_FiscalPropertyNumber(1037)
    driver.put_FiscalPropertyType(5)
    driver.ReadFiscalProperty()
    rn = driver.get_FiscalPropertyValue().strip()
    # Получем серийник ФН
    driver.put_RegisterNumber(47)
    driver.GetRegister()
    fn = driver.get_SerialNumber().strip()
    # Все норм, бибикаем
    beep()

def aReport(mode, type):
    setMode(mode)
    driver.put_ReportType(type)
    driver.Report()
    errorCheck()

def simpleCheck(data):
    # Режим регистрации
    setMode(1)
    # Картинка из памяти
    #driver.put_PictureNumber(2)
    #driver.put_LeftMargin(120)
    #driver.PrintPictureByNumber()
    #errorCheck()
    # Метод выполняет GetStatus(), SetMode(), CancelCheck() см. руководство программиста
    driver.NewDocument()
    errorCheck()
    # Тип чека
    driver.put_CheckType(data['check_type'])
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
    # Сумма оплаты
    driver.put_Summ(data['sum'])
    # Регистрация платежа
    driver.Payment()
    errorCheck()
    # Закрытие чека.
    driver.CloseCheck()
    errorCheck()
    # Получаем номер смены и номер чека
    driver.GetCurrentStatus()
    errorCheck()

    check = {}

    check['session'] = driver.get_Session()
    check['number'] = driver.get_CheckNumber()

    # Дата/Время последнего чека, тип чека, номер ФД чека, сумма чека, ФП
    driver.put_RegisterNumber(51)
    driver.GetRegister()
    check['r51_date'] = driver.get_Date()
    check['r51_time'] = driver.get_Time()
    check['r51_type'] = driver.get_CheckType()
    check['r51_number'] = driver.get_DocNumber()
    check['r51_summ'] = driver.get_Summ()
    check['r51_value'] = driver.get_Value()

    # Дата/Время последнего фискального документа, его номер, ФП
    driver.put_RegisterNumber(52)
    driver.GetRegister()
    check['r52_date'] = driver.get_Date()
    check['r52_time'] = driver.get_Time()
    check['r52_number'] = driver.get_DocNumber()
    check['r52_value'] = driver.get_Value()

    return check

def beep():
    driver.Beep()
    errorCheck()

def display(caption):
    p = serial.Serial('/dev/' + sys.argv[2], 9600)
    try:
        # Инициализация PD2800 в режиме протокола EPSON
        p.write('\x1B\x3D\x02\x1B\x74\x06\x1B\x52\x00\x0C' + str(caption).encode('cp866'))
        p.flushOutput()
        p.close()
    except:
        pass

busy = False

def newClient(client, server):
    server.send_message(client, json.dumps({ 'result': 'OK', 'method': 'rn', 'value': rn }))
    
def messageReceived(client, server, message):
    global busy

    if (busy):
        server.send_message(client, json.dumps({ 'result': 'ERR', 'type': 'busy', 'value': 'Сервер занят выполнением команды' }))
        return

    busy = True

    try:
        data = json.loads(message)

        if (data['method'] == 'ping'):
            # Дергается время от времени, что-бы проверить не отвалился-ли ФР
            driver.GetCurrentStatus()
            errorCheck(True)
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'value': 'pong' }))
            return

        if (data['method'] == 'status'):
            # Дергается перед пробитием чека, что-бы проверить не отвалился-ли ФР
            driver.GetStatus()
            errorCheck(True)
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'] }))
            return

        if (data['method'] == 'check'):
            # Пробить чек
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'value': simpleCheck(data['data']) }))
            return

        if (data['method'] == 'z'):
            # Z-Отчет
            aReport(3, 1)
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'] }))
            return
            
        if (data['method'] == 'x'):
            # X-Отчет
            aReport(2, 2)
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'] }))
            return

        if (data['method'] == 'display'):
            # Вывести что-то на дисплей покупателя
            display(data['data'])
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'] }))
            return
            
        server.send_message(client, json.dumps({ 'result': 'ERR', 'method': data['method'], 'type': 'invalid', 'value': 'Unknown method' }))

    except Exception as e:
        server.send_message(client, json.dumps({ 'result': 'ERR', 'type': type(e).__name__, 'value': e.args[0] }))

    finally:
        busy = False

try:
    init()
    # 2x20 - две строки по 20 символов
    display('****************************************')

    server = WebsocketServer(9111)

    server.set_fn_message_received(messageReceived)
    server.set_fn_new_client(newClient)
    server.run_forever()

except Exception as e:
    print(str(e))
    sys.exit()

