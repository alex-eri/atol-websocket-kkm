#!/usr/bin/python
# -*- coding:utf-8 -*-

import json
import os
import signal
import sys
import time
from multiprocessing import Queue
from threading import Thread

from libfptr10 import IFptr
from websocket_server import WebsocketServer

if sys.version[0] == '2':
    reload(sys)
#pylint: disable-msg=E1101
    sys.setdefaultencoding("utf-8")

fptr = IFptr("./fptr/libfptr10.so")

queue = Queue()
exit = False
fn = ""

class EFptrException(Exception):
    pass

class Runner(Thread):
    def run(self):
        a = 0
        while not exit:
            a = a + 1
            if a > 50:
                fptr.setParam(IFptr.LIBFPTR_PARAM_DATA_TYPE, IFptr.LIBFPTR_DT_STATUS)
                fptr.queryData()
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

    if fptr.errorCode() != 0:
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
            raise EFptrException('[' + str(fptr.errorCode()) + '] ' + fptr.errorDescription())

def setTableValue(table, row, field, value):
    # Запись в таблицу настроек фискального регистратора
    fptr.setParam(IFptr.LIBFPTR_PARAM_TABLE, table)
    fptr.setParam(IFptr.LIBFPTR_PARAM_ROW, row)
    fptr.setParam(IFptr.LIBFPTR_PARAM_FIELD, field)
    fptr.setParam(IFptr.LIBFPTR_PARAM_FIELD_VALUE, value)
    fptr.writeDeviceSettingRaw()
    errorCheck()

def setFRSetting(setting, value):
    # Запись настроек фискального регистратора
    fptr.setParam(IFptr.LIBFPTR_PARAM_SETTING_ID, setting)
    fptr.setParam(IFptr.LIBFPTR_PARAM_SETTING_VALUE, value)
    fptr.writeDeviceSetting()
    errorCheck()

def setFiscalProperty(property, value, checkForError = True):
    fptr.setParam(property, value)
    if checkForError:
        errorCheck()

def fptrInit():
    global fn

    fptr.setSingleSetting(IFptr.LIBFPTR_SETTING_PORT, str(IFptr.LIBFPTR_PORT_USB))
    fptr.applySingleSettings()

    fptr.open()

    fptr.cancelReceipt()

    if (len(sys.argv) > 1 and sys.argv[1] == 'init'):
        # Отключаем печать способа и признака расчета в позициях (116 и 117)
        setTableValue(2, 1, 116, 0)
        setTableValue(2, 1, 117, 0)
        # Шаблон чека №1
        setTableValue(2, 1, 111, 1)
        # Яркость печати
        setTableValue(2, 1, 19, 7)
        # Отключаем печать названия секции
        setTableValue(2, 1, 15, 0)
        # Шрифт
        setTableValue(2, 1, 32, 3)
        # Клише и Реклама
        fptr.clearPictures()
        errorCheck()
        fptr.setParam(IFptr.LIBFPTR_PARAM_FILENAME, "lanta.png")
        fptr.setParam(IFptr.LIBFPTR_PARAM_SCALE_PERCENT, 100.0)
        fptr.uploadPictureFromFile()
        errorCheck()
        setFRSetting(184, "")
        setFRSetting(185, u"                 Ждем Вас снова!")
        setFRSetting(186, "")
        setFRSetting(187, "")
        setFRSetting(188, "")
        setFRSetting(189, u"¶1,225¶")
        setFRSetting(190, u"                    42-99-99")
        setFRSetting(191, "")
        # Кол-во строк рекламы и строк клише всего
        setFRSetting(35, 4)
        setFRSetting(14, 8)
        # Канал обмена данными с ОФД - Ethernet
        setFRSetting(276, 2)
        # Применяем измененные данные 
        fptr.commitSettings()
        errorCheck()

    # Серийник ФН
    fptr.setParam(IFptr.LIBFPTR_PARAM_FN_DATA_TYPE, IFptr.LIBFPTR_FNDT_FN_INFO)
    fptr.fnQueryData()
    errorCheck()
    fn = str(fptr.getParamString(IFptr.LIBFPTR_PARAM_SERIAL_NUMBER)).strip().zfill(16)

    # Все норм, бибикаем
    beep()

    # Если режим инициализации то выходим
    if (len(sys.argv) > 1 and sys.argv[1] == 'init'):
        sys.exit()

def aReport(report, data):
    # Номер смены и чека (количество чеков в смене)
    fptr.setParam(IFptr.LIBFPTR_PARAM_FN_DATA_TYPE, IFptr.LIBFPTR_FNDT_SHIFT)
    fptr.fnQueryData()
    errorCheck()

    shift = fptr.getParamInt(IFptr.LIBFPTR_PARAM_SHIFT_NUMBER)
    receipt = fptr.getParamInt(IFptr.LIBFPTR_PARAM_RECEIPT_NUMBER)

    fptr.setParam(IFptr.LIBFPTR_PARAM_REPORT_TYPE, report)
    fptr.report()
    errorCheck()

    fptr.setParam(IFptr.LIBFPTR_PARAM_FN_DATA_TYPE, IFptr.LIBFPTR_FNDT_LAST_DOCUMENT)
    fptr.fnQueryData()
    fp = str(fptr.getParamString(IFptr.LIBFPTR_PARAM_FISCAL_SIGN)).strip().split('.')[0].zfill(10)
    errorCheck()

    # В зависимости от версии либо строка либо массив
    if ('version' in data and data['version'] >= 2):
        return { 'check': fn + ':' + fp, 'change': 0, 'shift': shift, 'receipt': receipt, 'version': 3 }
    else:
        return fn + ':' + fp

def check(data):
    # Открыть смену (если она закрыта)
    if (not sessionOpened()):
        operatorLogin(data)
        fptr.openShift()
    # Печать перед основным чеком
    if ('slip' in data and data['slip']):
        frPrint(data['slip'])
    operatorLogin(data)
    # Тип чека
    fptr.setParam(IFptr.LIBFPTR_PARAM_RECEIPT_TYPE, data['check_type'])
    # Открытие чека
    fptr.openReceipt()
    errorCheck()
    # Email или телефон покупателя (ОФД отправит электронный чек)
    if ('report' in data and data['report']):
        setFiscalProperty(1008, data['report'])
    # Наличность в кассе проверяем только для наличной оплаты (0)
    fptr.setParam(IFptr.LIBFPTR_PARAM_CHECK_SUM, data['payment_type'] == 0)
    # Позици чека
    for p in data['positions']:
        # Штрихкод (серийный номер, uid или прочий идентификатор), если есть (печатаем нефискально)
        if ('barcode' in p and p['barcode']):
            fptr.setParam(IFptr.LIBFPTR_PARAM_TEXT, p['barcode'])
            fptr.printText()
        # Наименование товара
        fptr.setParam(IFptr.LIBFPTR_PARAM_COMMODITY_NAME, p['name'])
        # Цена товара
        fptr.setParam(IFptr.LIBFPTR_PARAM_PRICE, p['price'])
        # Количество товара
        fptr.setParam(IFptr.LIBFPTR_PARAM_QUANTITY, p['quantity'])
        # Налог
        fptr.setParam(IFptr.LIBFPTR_PARAM_TAX_TYPE, p['tax'])
        # Сумма строки (позиции)
        fptr.setParam(IFptr.LIBFPTR_PARAM_POSITION_SUM, p['sum'])
        # Предмет расчета 
        fptr.setParam(1212, p['type'])
        # Способ расчета
        fptr.setParam(1214, p['payment'])
        # Регистрация позиции
        fptr.registration()
        errorCheck()
    # Номер исходного документа
    if ('reason' in data and data['reason']):
        fptr.setParam(1192, data['reason'])
        errorCheck()
    # Тип оплаты
    fptr.setParam(IFptr.LIBFPTR_PARAM_PAYMENT_TYPE, data['payment_type'])
    # Сумма оплаты
    fptr.setParam(IFptr.LIBFPTR_PARAM_PAYMENT_SUM, data['sum'])
    # Регистрация платежа
    fptr.payment()
    errorCheck()
    # Сдача
    change = fptr.getParamDouble(IFptr.LIBFPTR_PARAM_CHANGE)
    # Закрытие чека.
    fptr.closeReceipt()
    errorCheck()
    # Номер ФД чека
    fptr.setParam(IFptr.LIBFPTR_PARAM_FN_DATA_TYPE, IFptr.LIBFPTR_FNDT_LAST_DOCUMENT)
    fptr.fnQueryData()
    errorCheck()
    fp = str(fptr.getParamString(IFptr.LIBFPTR_PARAM_FISCAL_SIGN)).strip().split('.')[0].zfill(10)
    # Номер смены и чека
    fptr.setParam(IFptr.LIBFPTR_PARAM_FN_DATA_TYPE, IFptr.LIBFPTR_FNDT_SHIFT)
    fptr.fnQueryData()
    errorCheck()
    # В зависимости от версии либо строка либо массив
    if ('version' in data and data['version'] >= 2):
        return { 'check': fn + ':' + fp, 'change': change, 'shift': fptr.getParamInt(IFptr.LIBFPTR_PARAM_SHIFT_NUMBER), 'receipt': fptr.getParamInt(IFptr.LIBFPTR_PARAM_RECEIPT_NUMBER), 'version': 3 }
    else:
        return fn + ':' + fp

def beep():
    fptr.beep()
    errorCheck()

def printLine(l):
    fptr.setParam(IFptr.LIBFPTR_PARAM_TEXT, l)
    fptr.printText()
    errorCheck()

def frPrint(lines):
    for l in lines:
        if (len(l) > 0 and ord(l[0]) == 1) or (len(l) > 0 and len(l) < 5 and l.find('@') >= 0):
            fptr.cut()
            errorCheck()
        else:
            printLine(l)
    fptr.setParam(IFptr.LIBFPTR_PARAM_PICTURE_NUMBER, 1)
    fptr.setParam(IFptr.LIBFPTR_PARAM_ALIGNMENT, IFptr.LIBFPTR_ALIGNMENT_LEFT)
    fptr.setParam(IFptr.LIBFPTR_PARAM_LEFT_MARGIN, 225)
    fptr.printPictureByNumber()
    errorCheck()
    printLine(u"                    42-99-99")
    printLine("")

def sessionOpened():
    fptr.setParam(IFptr.LIBFPTR_PARAM_DATA_TYPE, IFptr.LIBFPTR_DT_SHIFT_STATE)
    fptr.queryData()
    errorCheck()

    return fptr.getParamInt(IFptr.LIBFPTR_PARAM_SHIFT_STATE) == IFptr.LIBFPTR_SS_OPENED

def operatorLogin(data):
    # Имя кассира
    if ('cashier' in data and data['cashier']):
        setFiscalProperty(1021, data['cashier'], False)
    # ИНН кассира
    if ('cashier_inn' in data and data['cashier_inn']):
        setFiscalProperty(1203, data['cashier_inn'], False)
    fptr.operatorLogin()

def processMessage(client, server, message):
    try:
        data = json.loads(message)

        if ('refer' in data and data['refer']):
            refer = data['refer']
        else:
            refer = False

        if (data['method'] == 'ping'):
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'value': 'pong', 'opened': sessionOpened(), 'fn': fn, 'version': 3, 'refer': refer }))
            return

        if (data['method'] == 'check'):
            fptr.cancelReceipt()
            # Пробить чек
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'value': check(data['data']), 'opened': sessionOpened(), 'refer': refer }))
            return

        if (data['method'] == 'report_z'):
            fptr.cancelReceipt()
            operatorLogin(data)
            # Z-Отчет
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'value': aReport(IFptr.LIBFPTR_RT_CLOSE_SHIFT, data), 'opened': sessionOpened(), 'refer': refer }))
            return

        if (data['method'] == 'report_x'):
            fptr.cancelReceipt()
            # X-Отчет
            aReport(IFptr.LIBFPTR_RT_X, data)
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'refer': refer }))
            return

        if (data['method'] == 'report_c'):
            fptr.cancelReceipt()
            # Отчет по кассирам
            aReport(IFptr.LIBFPTR_RT_OPERATORS, data)
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'refer': refer }))
            return

        if (data['method'] == 'open'):
            fptr.cancelReceipt()
            operatorLogin(data)
            # Открытие смены
            fptr.openShift()
            errorCheck()
            errorCheck()
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'opened': sessionOpened(), 'refer': refer }))
            return

        if (data['method'] == 'cash_in'):
            fptr.cancelReceipt()
            operatorLogin(data)
            # Внесение наличных в кассу
            fptr.setParam(IFptr.LIBFPTR_PARAM_SUM, data['cash'])
            fptr.cashIncome()
            errorCheck()
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'opened': sessionOpened(), 'refer': refer }))
            return

        if (data['method'] == 'cash_out'):
            fptr.cancelReceipt()
            operatorLogin(data)
            # Инкассация
            fptr.setParam(IFptr.LIBFPTR_PARAM_SUM, data['cash'])
            fptr.cashOutcome()
            errorCheck()
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'refer': refer }))
            return

        if (data['method'] == 'cancel'):
            # Аннуляция чека
            fptr.cancelReceipt()
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'refer': refer }))
            return

        if (data['method'] == 'print'):
            # Печать нефискальных данных
            fptr.cancelReceipt()
            frPrint(data['data'])
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'refer': refer }))
            return

        if (data['method'] == 'fn'):
            # Серийник ФН
            server.send_message(client, json.dumps({ 'result': 'OK', 'method': data['method'], 'value': fn, 'refer': refer }))
            return

        server.send_message(client, json.dumps({ 'result': 'ERR', 'method': data['method'], 'type': 'invalid', 'value': 'Unknown method', 'refer': refer }))

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

    runner = Runner()
    runner.start()

    server = WebsocketServer(9111, '0.0.0.0')
    server.set_fn_message_received(messageReceived)

    server.run_forever()

except Exception as e:
    print(str(e))
    exit = True
    sys.exit()
