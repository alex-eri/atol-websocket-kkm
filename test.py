#!/usr/bin/python
# -*- coding:utf-8 -*-

import sys
if sys.version[0] == '2':
    reload(sys)
#pylint: disable-msg=E1101
    sys.setdefaultencoding("utf-8")

import os
from libfptr10 import IFptr

fptr = IFptr("fptr/libfptr10.so")

fptr.setSingleSetting(IFptr.LIBFPTR_SETTING_PORT, str(IFptr.LIBFPTR_PORT_USB))
fptr.applySingleSettings()

fptr.open()

print("{} [{}]".format(fptr.errorCode(), fptr.errorDescription()))

#fptr.setParam(IFptr.LIBFPTR_PARAM_REPORT_TYPE, IFptr.LIBFPTR_RT_LAST_DOCUMENT)
#fptr.report()

#fptr.setParam(IFptr.LIBFPTR_PARAM_REPORT_TYPE, IFptr.LIBFPTR_RT_X)
#fptr.report()

#fptr.setParam(IFptr.LIBFPTR_PARAM_REPORT_TYPE, IFptr.LIBFPTR_RT_CLOSE_SHIFT)
#fptr.report()

#fptr.checkDocumentClosed()
#if fptr.printText() < 0:
#print("{} [{}]".format(fptr.errorCode(), fptr.errorDescription()))

# Регистрация кассира
#fptr.setParam(1021, u"Иванов И.И.")
#fptr.setParam(1203, u"500100732259")
#fptr.operatorLogin()
#
# Открытие чека(с передачей телефона получателя)
#fptr.setParam(IFptr.LIBFPTR_PARAM_RECEIPT_TYPE, IFptr.LIBFPTR_RT_SELL)
#fptr.setParam(1008, u"mmikel@mail.ru")
#fptr.openReceipt()
#
# Регистрация позиции
#fptr.setParam(IFptr.LIBFPTR_PARAM_COMMODITY_NAME, u"Чипсы LAYS")
#fptr.setParam(IFptr.LIBFPTR_PARAM_PRICE, 74)
#fptr.setParam(IFptr.LIBFPTR_PARAM_QUANTITY, 5)
#fptr.setParam(IFptr.LIBFPTR_PARAM_TAX_TYPE, IFptr.LIBFPTR_TAX_VAT18)
#fptr.setParam(1212, 1)
#fptr.setParam(1214, 7)
#fptr.registration()
#
# Регистрация итога (отрасываем копейки)
#fptr.setParam(IFptr.LIBFPTR_PARAM_SUM, 369.0)
#fptr.receiptTotal()
#
# Оплата наличными
#fptr.setParam(IFptr.LIBFPTR_PARAM_PAYMENT_TYPE, IFptr.LIBFPTR_PT_CASH)
#fptr.setParam(IFptr.LIBFPTR_PARAM_PAYMENT_SUM, 1000)
#fptr.payment()
#
# Закрытие чека
#fptr.closeReceipt()
#
# Запрос информации о закрытом чеке
#fptr.setParam(IFptr.LIBFPTR_PARAM_FN_DATA_TYPE, IFptr.LIBFPTR_FNDT_LAST_DOCUMENT)
#fptr.fnQueryData()
#print("Fiscal Sign = {}".format(fptr.getParamString(IFptr.LIBFPTR_PARAM_FISCAL_SIGN)))
#print("Fiscal Document Number = {}".format(fptr.getParamInt(IFptr.LIBFPTR_PARAM_DOCUMENT_NUMBER)))
#
#fptr.setParam(IFptr.LIBFPTR_PARAM_FN_DATA_TYPE, IFptr.LIBFPTR_FNDT_FN_INFO)
#fptr.fnQueryData()
#
#print(fptr.getParamString(IFptr.LIBFPTR_PARAM_SERIAL_NUMBER))

fptr.setParam(IFptr.LIBFPTR_PARAM_TABLE, 2)
fptr.setParam(IFptr.LIBFPTR_PARAM_ROW, 1)
fptr.setParam(IFptr.LIBFPTR_PARAM_FIELD, 19)
fptr.setParam(IFptr.LIBFPTR_PARAM_FIELD_VALUE, 8)

fptr.writeDeviceSettingRaw()
print("{} [{}]".format(fptr.errorCode(), fptr.errorDescription()))

fptr.commitSettings()
print("{} [{}]".format(fptr.errorCode(), fptr.errorDescription()))

#fptr.setParam(IFptr.LIBFPTR_PARAM_DATA_TYPE, IFptr.LIBFPTR_DT_STATUS)
#fptr.queryData()
#
#print(fptr.getParamInt(IFptr.LIBFPTR_PARAM_SHIFT_NUMBER))

#fptr.setParam(IFptr.LIBFPTR_PARAM_DATA_TYPE, IFptr.LIBFPTR_DT_SHIFT_STATE)
#fptr.queryData()
#
#print(fptr.getParamInt(IFptr.LIBFPTR_PARAM_SHIFT_STATE) == IFptr.LIBFPTR_SS_OPENED)

#print(IFptr.LIBFPTR_TAX_VAT18)

