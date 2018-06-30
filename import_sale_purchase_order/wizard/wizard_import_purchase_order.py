#-*- coding: utf-8 -*-

import os
import csv
import tempfile
import base64
from odoo.exceptions import UserError
from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import datetime, timedelta, date


class ImportPurchaseOrder(models.TransientModel):
    _name = "wizard.import.purchase.order"

    file_data = fields.Binary('Archivo', required=True,)
    file_name = fields.Char('File Name')
    partner_id = fields.Many2one('res.partner', string='Proveedor', required=True,domain=[('supplier', '=', True)])


    def import_button(self):
        if not self.csv_validator(self.file_name):
            raise UserError(_("El archivo debe ser de extension .csv"))
        file_path = tempfile.gettempdir()+'/file.csv'
        data = self.file_data
        f = open(file_path,'wb')
        f.write(base64.b64decode(data))
        #f.write(data.decode('base64'))
        f.close() 
        archive = csv.DictReader(open(file_path))
        
        purchase_order_obj = self.env['purchase.order']
        product_obj = self.env['product.product']
        product_template_obj = self.env['product.template']
        purchase_order_line_obj = self.env['purchase.order.line']
        
        archive_lines = []
        for line in archive:
            archive_lines.append(line)
            
        self.valid_columns_keys(archive_lines)
        self.valid_product_code(archive_lines, product_obj)
        self.valid_prices(archive_lines)
        
        vals = {
            'partner_id': self.partner_id.id,
            'date_planned': datetime.now(),
        }
        purchase_order_id = purchase_order_obj.create(vals)
        cont = 0
        for line in archive_lines:
            cont += 1
            code = str(line.get('code',""))
            product_id = product_obj.search([('default_code','=',code)])
            quantity = line.get('quantity',0)
            price_unit = self.get_valid_price(line.get('price',""),cont)
            product_uom = product_template_obj.search([('default_code','=',code)])
            if purchase_order_id and product_id:
                vals = {
                    'order_id': purchase_order_id.id,
                    'product_id': product_id.id,
                    'product_qty': float(quantity),
                    'price_unit': price_unit,
                    'date_planned': datetime.now(),
                    'product_uom': product_id.product_tmpl_id.uom_po_id.id,
                    'name': product_id.name,
                }
                purchase_order_line_obj.create(vals)
        return {'type': 'ir.actions.act_window_close'}
        
    @api.model
    def valid_prices(self, archive_lines):
        cont = 0
        for line in archive_lines:
            cont += 1
            price = line.get('price',"")
            if price != "":
                price = price.replace("$","").replace(",",".")
            try:
                price_float = float(price)
            except:
                raise UserError('El precio del producto de la linea %s, no tiene formato adecuado. Formatos adecuados, ejemplo: "$100,00"-"100,00"-"100"'%cont)
        return True

    @api.model
    def get_valid_price(self, price, cont):
        if price != "":
            price = price.replace("$","").replace(",",".")
        try:
            price_float = float(price)
            return price_float
        except:
            raise UserError('El precio del producto de la linea %s, no tiene formato adecuado. Formatos adecuados, ejemplo: "$100,00"-"100,00"-"100"'%cont)
        return False
    
    @api.model
    def valid_product_code(self, archive_lines, product_obj):
        cont=0
        for line in archive_lines:
            cont += 1
            code = str(line.get('code',"")).strip()
            product_id = product_obj.search([('default_code','=',code)])
            if len(product_id)>1:
                raise UserError("El código del producto de la linea %s, esta duplicado en el sistema."%cont)
            if not product_id:
                raise UserError("El código del producto de la linea %s, no se encuentra en el sistema."%cont)
            
    @api.model
    def valid_columns_keys(self, archive_lines):
        columns = archive_lines[0].keys()
        text = "El Archivo csv debe contener las siguientes columnas: code, quantity y price. \nNo se encuentran las siguientes columnas en el Archivo:"; text2 = text
        if not 'code' in columns:
            text +="\n[ code ]"
        if not 'quantity' in columns:
            text +="\n[ quantity ]"
        if not 'price' in columns:
            text +="\n[ price ]"
        if text !=text2:
            raise UserError(text)
        return True
            
        
    @api.model
    def csv_validator(self, xml_name):
        name, extension = os.path.splitext(xml_name)
        return True if extension == '.csv' else False
        
