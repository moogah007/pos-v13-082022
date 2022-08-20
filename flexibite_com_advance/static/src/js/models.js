odoo.define('flexibite_com_advance.models', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var _t = core._t;
    var utils = require('web.utils');
    var session = require('web.session');

    var round_pr = utils.round_precision;
    var QWeb = core.qweb;

    models.load_fields("res.users", ['pos_category_ids','access_send_order_kitchen','image_128','login','company_ids','access_ereceipt','access_quick_cash_payment',
                                     'access_order_note','access_product_note','access_pos_return','access_reorder',
                                     'access_draft_order','access_bag_charges','access_delivery_charges',
                                     'access_pos_lock','access_keyboard_shortcut','access_product_sync','access_display_warehouse_qty',
                                     'access_change_stock_locations','access_pos_graph','access_x_report','access_pos_loyalty',
                                     'access_today_sale_report','access_money_in_out','access_gift_card','access_gift_voucher',
                                     'access_print_last_receipt','access_pos_promotion','lock_terminal','delete_msg_log','access_show_qty',
                                     'access_print_valid_days','access_card_charges','access_wallet','access_print_cash_statement','change_sales_person',
                                     'discard_product','based_on','can_give_discount', 'discount_limit','login_with_pos_screen','store_ids','access_pos_dashboard',
                                     'access_product_expiry_report','pos_user_type','sales_persons','display_own_sales_order','default_store_id','partner_id',
                                     'access_print_ledger','access_default_customer','rfid_no','pos_security_pin','access_create_purchase_order','access_combo']);
    models.load_fields("res.partner", ['display_name','prefer_ereceipt','remaining_loyalty_points',
                                       'remaining_loyalty_amount', 'loyalty_points_earned',
                                       'total_remaining_points','remaining_wallet_amount','credit_limit',
                                       'property_product_pricelist','remaining_credit_amount', 'birth_date',
                                       'property_account_receivable_id','parent_id','remaining_debit_amount','debit_limit']);
    models.load_fields("product.product", ['sequence','qty_available','type','is_packaging','product_brand_id','loyalty_point',
                                           'is_dummy_product','invoice_policy','return_valid_days','non_refundable','write_date',
                                            'lst_price','product_template_attribute_value_ids','priority','send_to_kitchen','is_combo','product_combo_ids']);
    models.load_fields("product.category", ['complete_name']);
    models.load_fields('pos.session',['cash_register_id','is_lock_screen','current_cashier_id','locked','locked_by_user_id','opening_balance','store_id','increment_number']);
    models.load_fields("pos.payment.method", ['apply_charges', 'fees_amount', 'fees_type',
                       'optional','shortcut_key','jr_use_for','split_transactions']);
    models.load_fields("res.company", ['payment_total','pos_price', 'pos_quantity', 'pos_discount', 'pos_search', 'pos_next']);
    models.load_fields("pos.category", ['loyalty_point','return_valid_days']);

    models.PosModel.prototype.models.push({
        model:  'quick.cash.payment',
        fields: ['display_name','name'],
        loaded: function(self,quick_pays){
            self.quick_pays = quick_pays;
            self.db.add_quick_payment(quick_pays);
        },
    },{
        model: 'stock.location',
        fields: [],
        domain: function(self) { return [['usage', '=', 'internal'],['company_id','=',self.config.company_id[0]]]; },
        loaded: function(self, locations){
            if(locations && locations[0]){
                self.location_ids = locations;
                self.locations_by_id = {};
                _.each(locations,function(loc){
                    self.locations_by_id[loc.id] = loc;
                });
            }
        },
    },{
        model:  'pos.store',
        fields: [],
        domain: function(self){return[['company_id','=',self.company.id]]},
        loaded: function(self,pos_store){
            self.store_by_id = {};
            _.each(pos_store, function(store) {
                self.store_by_id[store.id] = store;
            });
        },
    },{
        model:  'product.combo',
        fields: [],
        loaded: function(self,product_combo){
            self.product_combo = product_combo;
        },
    },{
        model: 'product.brand',
        fields: [],
        loaded: function(self, brands){
            if(brands){
                self.db.add_brands(brands)
            }
        },
    },{
        model:  'aspl.gift.card.type',
        fields: ['name'],
        loaded: function(self,card_type){
            self.card_type = card_type;
        },
    },{
        model: 'mrp.bom',
        domain: function(self) { return [['available_in_pos', '=', true]]; },
        loaded: function(self, mrp_bom){
            self.db.add_prod_bom(mrp_bom);
            self.prod_mrp_bom_data = mrp_bom;
        },
    },{
        model: 'mrp.bom.line',
        domain: function(self) { return [['id', 'in', self.db.bom_line_ids]]; },
        fields: ['product_id','parent_product_tmpl_id','bom_id'],
        loaded: function(self, mrp_bom_line_data){            
            self.prod_bom_line_data = mrp_bom_line_data;
            self.bom_line_by_id = {};
            _.each(mrp_bom_line_data,function(each_bom_line_id){
                self.bom_line_by_id[each_bom_line_id.id] = each_bom_line_id;
                each_bom_line_id['select'] = true
            });
        },
    },{
        model:  'pos.promotion',
        fields: [],
        domain: function(self){
            var current_date = moment(new Date()).locale('en').format("YYYY-MM-DD");
            var weekday = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
            var current_time = moment(new Date().getTime()).locale('en').format("H");
            var d = new Date();
            var current_day = weekday[d.getDay()]
            return [['from_date','<=',current_date],['to_date','>=',current_date],['active','=',true],
                    ['day_of_week_ids.name','in',[current_day]]];
        },
        loaded: function(self, pos_promotions){
            self.pos_promotions = pos_promotions;
        },
    },{
        model:  'pos.conditions',
        fields: [],
        loaded: function(self,pos_conditions){
            self.pos_conditions = pos_conditions;
        },
    },{
        model:  'get.discount',
        fields: [],
        loaded: function(self,pos_get_discount){
            self.pos_get_discount = pos_get_discount;
        },
    },{
        model:  'quantity.discount',
        fields: [],
        loaded: function(self,pos_get_qty_discount){
            self.pos_get_qty_discount = pos_get_qty_discount;
        },
    },{
        model:  'quantity.discount.amt',
        fields: [],
        loaded: function(self,pos_qty_discount_amt){
            self.pos_qty_discount_amt = pos_qty_discount_amt;
        },
    },{
        model:  'discount.multi.products',
        fields: [],
        loaded: function(self,pos_discount_multi_prods){
            self.pos_discount_multi_prods = pos_discount_multi_prods;
        },
    },{
        model:  'discount.multi.categories',
        fields: [],
        loaded: function(self,pos_discount_multi_categ){
            self.pos_discount_multi_categ = pos_discount_multi_categ;
        },
    },{
        model:  'discount.above.price',
        fields: [],
        loaded: function(self,pos_discount_above_price){
            self.pos_discount_above_price = pos_discount_above_price;
        },
    },{
        model:  'message.terminal',
        fields: [],
        domain: function(self) { return [['message_session_id', '=', self.pos_session.id]]; },
        loaded: function(self,message_list){
            self.message_list = message_list;
        },
    },{
        model:  'stock.picking.type',
        fields: [],
        domain: [['code','=','internal']],
        loaded: function(self,stock_pick_typ){
            self.stock_pick_typ = stock_pick_typ;
            self.db.add_picking_types(stock_pick_typ);
        },
    },{
        model:  'product.attribute',
        fields: [ 'name',
                  'attribute_line_ids',
                  'value_ids',
                ],
        loaded: function(self,attributes){
            self.db.add_product_attributes(attributes);
        },
    },{
        model:  'product.attribute.value',
        fields: [  'name',
                   'attribute_id',
                ],
        loaded: function(self,values){
            self.db.add_product_attribute_values(values);
        },
    }/*{
        model:  'product.attribute',
        fields: [ 'name',
                  'value_ids',
                ],
        loaded: function(self,attributes){
            self.db.add_product_attributes(attributes);
        },
    },{
        model:  'product.attribute.value',
        fields: [  'name',
                   'attribute_id',
                ],
        loaded: function(self,values){
             self.db.add_product_attribute_values(values);
        },
    }*/,{
        model: 'aspl.gift.card',
        domain: [['is_active', '=', true]],
        loaded: function(self,gift_cards){
            self.db.add_giftcard(gift_cards);
            self.set({'gift_card_order_list' : gift_cards});
        },
    },{
        model: 'aspl.gift.voucher',
        domain: [],
        loaded: function(self,gift_vouchers){
            self.db.add_gift_vouchers(gift_vouchers);
            self.set({'gift_voucher_list' : gift_vouchers});
        },
    },{
        model:  'product.template.attribute.value',
        fields: [  'product_attribute_value_id',
                   'product_tmpl_id',
                   'attribute_id',
                   'ptav_product_variant_ids',
                ],
        loaded: function(self,values){
            self.db.product_template_attribute = values;
        },
    });
    function decimalAdjust(value){
        var split_value = value.toFixed(2).split('.');
        //convert string value to integer
        for(var i=0; i < split_value.length; i++){
            split_value[i] = parseInt(split_value[i]);
        }
        var reminder_value = split_value[1] % 10;
        var division_value = parseInt(split_value[1] / 10);
        var rounding_value;
        var nagative_sign = false;
        if(split_value[0] == 0 && value < 0){
            nagative_sign = true;
        }
        if(_.contains(_.range(0,5), reminder_value)){
            rounding_value = eval(split_value[0].toString() + '.' + division_value.toString() + '0' )
        }else if(_.contains(_.range(5,10), reminder_value)){
            rounding_value = eval(split_value[0].toString() + '.' + division_value.toString() + '5' )
        }
        if(nagative_sign){
            return -rounding_value;
        }else{
            return rounding_value;
        }
    }

    var posmodel_super = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: function(session, attributes) {
            var self = this;
            this.product_list = [];
            this.load_background = false;
            this.product_fields = ['qty_available','write_date'];
            this.product_domain = [];
            this.product_context = {display_default_code: false };
            this.all_pos_session = [];
            this.all_locations = [];
            this.shop = false;
            this.credit_amount = 0.00;
            this.increment_number = 0;
            this.last_token_number = 999;
            posmodel_super.initialize.call(this, session, attributes);
            this.kitchen_order_timer = {};
            this.set({
                'pos_order_list':[],
            });
            this.load_order_flag = false;
        },
        // mirror_kitchen_orders:function(new_order){
        //     console.log("mirror_kitchen_orders")
        //     return new Promise(function (resolve, reject) {
        //         rpc.query({
        //             model: 'pos.order',
        //             method: 'broadcast_order_data',
        //             args : [new_order]
        //         },{async:false}).then(function(result) {
        //             if(result){
        //                 resolve($('.kitchen-buttons .button.category.selected').trigger('click'))
        //             }
        //         });
        //     })
        // },
        print_receipt: function (receipt) {
            var self = this;
            var i = -1
            function ReceiptLoop(html) {
                setTimeout(function() {
                    if(html){
                        self.proxy.printer.print_receipt(html);
                    }
                    i+=1;
                    if (i < receipt.length) {
                        ReceiptLoop(receipt[i]);
                    }
                }, 1000)
            }
            ReceiptLoop();
        },

        mirror_kitchen_orders:function(new_order){
            var self = this;
            rpc.query({
                model: 'pos.order',
                method: 'broadcast_order_data',
                args : [new_order]
            }).then(function(pos_orders) {
                if(pos_orders && pos_orders[0]){
                    var categ_id = 0
                    if(self.chrome && self.chrome.screens && self.chrome.screens.kitchen_screen){
                        categ_id = self.chrome.screens.kitchen_screen.categ_id;
                    }
                    var screen_data = [];
                    _.each(pos_orders,function(order){
                        _.each(order.order_lines,function(line){
                            if(line.state != 'done' && line.state != 'cancel'){
                                screen_data.push(line);
                            }
                        });
                    });
                    self.set('screen_data',screen_data);
                    var screen_order_lines = [];
                    _.each(pos_orders,function(order){
                        _.each(order.order_lines,function(line){
                            if(categ_id == 0 && line.state != 'done' && line.state != 'cancel'){
                                screen_order_lines.push(line);
                            }
                            if(_.contains(self.user.pos_category_ids, line.prod_categ_id) && line.state != 'done' && line.state != 'cancel'){
                                screen_order_lines.push(line);
                            }
                        });
                    });
                    if(self.chrome && self.chrome.screens && self.chrome.screens.kitchen_screen){
                        self.chrome.screens.kitchen_screen.render_screen_order_lines(screen_order_lines);
                        self.chrome.screens.kitchen_screen.render_table_data(pos_orders);
                    }
                }else{
                    if(self.chrome && self.chrome.screens && self.chrome.screens.kitchen_screen){
                        self.chrome.screens.kitchen_screen.render_screen_order_lines([]);
                        self.chrome.screens.kitchen_screen.render_table_data([]);
                    }
                }
            });
        },
        get_product_has_bom : function (product){
            var data = _.filter(this.prod_mrp_bom_data, function(item) {
                 return product.product_tmpl_id == item.product_tmpl_id[0];
            });
            return data.length
        },
        set_title_detail_expire_screen:function(title){
            this.set('screen_title',title)
        },
        get_title_detail_expire_screen: function(){
            return this.get('screen_title');
        },
        is_product_loading: function () {
            return this.load_background;
        },
        load_new_products: function(){
            var self = this;
            var def  = new $.Deferred();
            var currency_symbol = self.currency ? self.currency : {symbol:'$', position: 'after', rounding: 0.01, decimals: 2};
            var fields = this.product_fields;
            var pos_domain = this.product_domain;
            var prod_domain = [['write_date','>',self.db.get_product_write_date()]]; 
            prod_domain = prod_domain.concat(pos_domain);
            var context = { 
                pricelist: self.default_pricelist.id,
                display_default_code: false,
                location : self.config.id,
                compute_child: false,
            };
            var write_date = self.db.get_product_write_date();
            var productPromise = new Promise(function(resolve, reject){
                rpc.query({
                    model: 'product.product',
                    method: 'load_latest_product',
                    args : [write_date,fields,context]
                }, {
                    timeout: 3000,
                    shadow: true,
                    async: false,
                }).then(function(res){
                    if(res){
                        resolve(res);
                    }else{
                        reject()
                    }
                })
            })
            return productPromise.then(function(res){
                self.db.currency_symbol = currency_symbol;
                if(res && res.variants){
                    var setup_prd = _.map(res.variants, function (product) {
                        product.categ = _.findWhere(self.product_categories, {'id': product.categ_id[0]});
                        return new models.Product({}, product);
                    });
                    var prod_obj = self.gui.screen_instances.products.product_list_widget;
                    var current_pricelist = prod_obj._get_active_pricelist();
                    _.map(setup_prd,function(product){
                        if(current_pricelist){
                            prod_obj.product_cache.clear_node(product.id+','+current_pricelist.id);
                            prod_obj.render_product(product);
                        }
                        prod_obj.renderElement();
                    });
                    self.db.add_products(setup_prd)
                }
                if(res && res.product_tmpl){
                    self.db.add_templates(_.map(res.product_tmpl, function(product) {
                        product.categ = _.findWhere(self.product_categories, {
                            'id': product.categ_id[0]
                        });
                        return new models.Product({}, product);
                    }));
                }
                self.gui.screen_instances.products.product_categories_widget.renderElement();
            })
        },
        load_new_partners: function(){
            var self = this;
            return new Promise(function (resolve, reject) {
                var fields = self.partner_fields;
                var domain = [['write_date','>',self.db.get_partner_write_date()]];
                rpc.query({
                    model: 'res.partner',
                    method: 'search_read',
                    args: [domain, fields],
                }, {
                    timeout: 3000,
                    shadow: true,
                })
                .then(function (partners) {
                    if (self.db.add_partners(partners)) {   // check if the partners we got were real updates
                        var partner = false;
                        if(self.get_client()){
                            partner = self.get_client();
                        }else{
                            partner =  partners[0];
                        }
                        if(partner){
                            self.gui.screen_instances.clientlist.display_client_details('show',partner,0);
                        }
                        resolve();
                    } else {
                        reject();
                    }
                }, function (type, err) { reject(); });
            });
        },
        load_server_data: function () {
            var self = this;
            self.system_parameters = false;
            self.user_by_id = {};
            self.is_rfid_login = false;

            /*Partner Object Remove*/
            var partner_index = _.findIndex(this.models, function (model) {
                return model.model === "res.partner";
            });
            var partner_model = this.models[partner_index];
            if (partner_index !== -1) {
                this.models.splice(partner_index, 1);
            }

            /*Product Object Remove*/
            var product_index = _.findIndex(this.models, function (model) {
                return model.model === "product.product";
            });
            var product_model = this.models[product_index];
            if (product_index !== -1) {
                this.models.splice(product_index, 1);
            }

            var RFIDPromise = new Promise(function (resolve, reject) {
                rpc.query({
                    model: 'pos.order',
                    method: 'load_ir_config_parameter',
                }).then(function(system_parameters){
                    resolve(system_parameters);
                }).catch(function(){
                    self.db.notification('danger',"Connection lost");
                });
            })
            RFIDPromise.then(function(system_parameters){
                if(system_parameters && system_parameters.length){
                    if(system_parameters[0].is_rfid_login){
                        self.is_rfid_login = true;
                    }
                    if(system_parameters[0].pos_theme){
                        self.current_pos_theme = system_parameters[0].pos_theme;
                    }
                }
            });
            // var Tokenpromise = new Promise(function (resolve, reject) {
            //     rpc.query({
            //         model: 'res.config.settings',
            //         method: 'load_settings',
            //         args: ['last_token_number']
            //     }).then(function(settings){
            //         resolve(settings);
            //     }).catch(function(){
            //         self.db.notification('danger',"Connection lost");
            //     });
            // })
            // Tokenpromise.then(function(settings){
            //     if(settings && settings[0] && Number(settings[0].last_token_number)){
            //         if(Number(settings[0].last_token_number) > 0){
            //             self.last_token_number = Number(settings[0].last_token_number);
            //         }
            //     }
            //     // if(system_parameters && system_parameters.length){
            //     //     if(system_parameters[0].is_rfid_login){
            //     //         self.is_rfid_login = true;
            //     //     }
            //     //     if(system_parameters[0].pos_theme){
            //     //         self.current_pos_theme = system_parameters[0].pos_theme;
            //     //     }
            //     // }
            // });

            return posmodel_super.load_server_data.apply(this, arguments).then(function () {
                if(self.config.generate_token){
                    var res_config_settings_params = {
                        model: 'res.config.settings',
                        method: 'load_settings',
                        args: ['last_token_number']
                    }
                    rpc.query(res_config_settings_params, {async: false})
                    .then(function(settings){
                        if(settings && settings[0] && Number(settings[0].last_token_number)){
                            if(Number(settings[0].last_token_number) > 0){
                                self.last_token_number = Number(settings[0].last_token_number);
                            }
                        }
                    });
                    var increment_number = Number(self.pos_session.increment_number || 0);
                    self.increment_number = increment_number + 1;
                }
                if(self.user){
                    self.employee = _.each(self.user, function(val, key){
                        if(key != 'name'){
                            self.employee[key] = val;
                        }
                    });
                }
                
                self.partner_fields =  typeof partner_model.fields === 'function'  ? partner_model.fields(self)  : partner_model.fields;
                self.partner_domain =  typeof partner_model.domain === 'function'  ? partner_model.domain(self)  : partner_model.domain;
                
                self.product_fields =  typeof product_model.fields === 'function'  ? product_model.fields(self)  : product_model.fields;
                self.product_domain =  typeof product_model.domain === 'function'  ? product_model.domain(self)  : product_model.domain;
                
                var SessionListPromise = new Promise(function (resolve, reject) {
                    rpc.query({
                        model: 'pos.session',
                        method: 'search_read',
                        domain: [['state','=','opened']],
                        fields: ['id','name','config_id'],
                        orderBy: [{ name: 'id', asc: true}],
                    }).then(function(sessions){
                        resolve(sessions);
                    }).catch(function(){
                        self.db.notification('danger',"Connection lost");
                    });
                });
                SessionListPromise.then(function(sessions){
                    if(sessions && sessions[0]){
                        self.all_pos_session = sessions;
                    }
                });

                var LoyaltyConfigPromise = new Promise(function (resolve, reject) {
                    rpc.query({
                        model: 'loyalty.config.settings',
                        method: 'load_loyalty_config_settings',
                    }).then(function(loyalty_config){
                        resolve(loyalty_config);
                    }).catch(function(){
                        self.db.notification('danger',"Connection lost");
                    });
                });
                LoyaltyConfigPromise.then(function(loyalty_config){
                    if(loyalty_config && loyalty_config[0]){
                        self.loyalty_config = loyalty_config[0];
                    }
                });

                self.set_lock_status(self.pos_session.locked);
                self.start_timer();
                _.each(self.users, function(user){
                    self.user_by_id[user.id] = user;
                });

                if(self.user.lock_terminal){
                    var LockTerminalPromise = new Promise(function(resolve, reject){
                        var params = {
                            model: 'lock.data',
                            method: 'search_read',
                            domain: [['session_id', '=', self.pos_session.id]],
                        }
                        rpc.query(params, {async: false}).then(function(lock_data){
                            if(lock_data && lock_data.length > 0){
                                resolve(lock_data);
                            }
                        })
                    }).catch(function(){
                        self.db.notification('danger',"Connection lost");
                    })
                    LockTerminalPromise.then(function(lock_data){
                        self.set_lock_data(lock_data[0])
                    })
                }

                if(self.config.print_audit_report || self.config.out_of_stock_detail){
                    var AuditReportPromise = new Promise(function (resolve, reject) {
                        rpc.query({
                            model: 'stock.location',
                            method: 'search_read',
                            domain: [['usage','=','internal'],['company_id','=',self.company.id]],
                            fields: ['id','name','company_id','complete_name'],
                        }).then(function(locations){
                            resolve(locations);
                        }).catch(function(){
                            self.db.notification('danger',"Connection lost");
                        });
                    });
                    AuditReportPromise.then(function(locations){
                        if(locations && locations[0]){
                            self.all_locations = locations;
                        }
                    });
                }


                /*if(self.config.pos_sale_order){
                    var date = new Date();
                    var domain;
                    var start_date;
                    self.domain_sale_order = [];
                    if(date){
                        if(self.config.sale_order_last_days){
                            date.setDate(date.getDate() - self.config.sale_order_last_days);
                        }
                        start_date = date.toJSON().slice(0,10);
                        self.domain_sale_order.push(['create_date' ,'>=', start_date]);
                    } else {
                        domain = [];
                    }
                    self.domain_sale_order.push(['state','not in',['cancel']]);
                    var sale_order_details = {
                        model: 'sale.order',
                        method: 'search_read',
                        domain: self.domain_sale_order
                    }
                    rpc.query(sale_order_details, {async: false}).then(function(orders){
                        self.db.add_sale_orders(orders);
                        if(self.user.display_own_sales_order){
                            var user_orders = [];
                            orders.map(function(sale_order){
                                if(sale_order.user_id[0] == self.user.id){
                                    user_orders.push(sale_order);
                                }
                            });
                            orders = user_orders;
                        }
                        orders.map(function(sale_order){
                            if(sale_order.date_order){
                                var dt = new Date(new Date(sale_order.date_order) + "GMT");
                                var n = dt.toLocaleDateString();
                                var crmon = self.addZero(dt.getMonth()+1);
                                var crdate = self.addZero(dt.getDate());
                                var cryear = dt.getFullYear();
                                var crHour = self.addZero(dt.getHours());
                                var crMinute = self.addZero(dt.getMinutes());
                                var crSecond = self.addZero(dt.getSeconds());
                                 sale_order.date_order = cryear + '/' + crmon +'/'+ crdate +' '+crHour +':'+ crMinute +':'+ crSecond;
                            }
                        });
                        self.set({'pos_sale_order_list' : orders});
                    });
                }*/

                if(self.config.enable_multi_store && self.pos_session.store_id && self.pos_session.store_id[0]){
                    self.load_background = true;
                    return
                }
                else{
                    var product_ids_list = [];
                    var product_fields = self.product_fields.concat(['name', 'display_name', 'product_variant_ids', 'product_variant_count'])
                    var PosCachePromise = new Promise(function(resolve, reject){
                        var params = {
                            model: 'pos.cache',
                            method: 'search',
                            args: [[['config_id', '=', self.pos_session.config_id[0]]]],
                        }
                        rpc.query(params, {async: false}).then(function(res){
                            if(res && res[0]){
                                resolve(res);
                            }else{
                                reject();
                            }
                        }).catch(function(){
                            self.db.notification('danger',"Connection lost")
                        })
                    })
                    PosCachePromise.then(function(res){
                        if(res && res[0]){
                            self.load_background = false;
                        }else{
                            self.load_background = true;
                        }
                    })

                }
            });
        },
        addZero: function(value){
            if (value < 10) {
                value = "0" + value;
            }
            return value;
        },
        create_sale_order: function(delivery_done){
            var self = this;
            var order = this.get_order();
            var currentOrderLines = order.get_orderlines();
            var customer_id = order.get_client().id;
            var location_id = self.config.stock_location_id ? self.config.stock_location_id[0] : false;
            var paymentlines = false;
            var paid = false;
            var confirm = false;
            var orderLines = [];
            for(var i=0; i<currentOrderLines.length;i++){
                orderLines.push(currentOrderLines[i].export_as_JSON());
            }
            if(self.config.sale_order_operations === "paid" || order.get_order_id() || order.get_edit_quotation()) {
                paymentlines = [];
                _.each(order.get_paymentlines(), function(paymentline){
                    paymentlines.push({
                        'journal_id': paymentline.cashregister.journal_id[0],
                        'amount': paymentline.get_amount(),
                    })
                });
                paid = true
            }
            if(self.config.sale_order_operations === "confirm" && !order.get_edit_quotation()){
                confirm = true;
            }
            var vals = {
                orderlines: orderLines,
                customer_id: customer_id,
                location_id: location_id,
                journals: paymentlines,
                pricelist_id: order.pricelist.id || false,
                partner_shipping_id: order.get_shipping_address() || customer_id,
                partner_invoice_id: order.get_invoice_address() || customer_id,
                note: order.get_sale_note() || "",
                signature: order.get_signature() || "",
                inv_id: order.get_inv_id() || false,
                order_date: order.get_sale_order_date() || false,
                commitment_date: order.get_sale_order_requested_date() || false,
                sale_order_id: order.get_order_id() || false,
                edit_quotation: order.get_edit_quotation() || false,
                warehouse_id: self.config.warehouse_id ? self.config.warehouse_id[0] : false,
            }
            var params = {
                model: 'sale.order',
                method: 'create_sales_order',
                args: [vals, {'confirm': confirm, 'paid': paid,'delivery_done':delivery_done}],
            }
            rpc.query(params, {async: false}).then(function(sale_order){
                if(sale_order && sale_order[0]){
                    sale_order = sale_order[0];
                    if(paid && order.get_paying_sale_order()){
                        $('#btn_so').show();
                        if(sale_order){
                            order.set_sale_order_name(sale_order.name);
                        }
                        self.gui.show_screen('receipt');
                    } else{
                        var edit = order.get_edit_quotation();
                        order.finalize();
                        var url = window.location.origin + '/web#id=' + sale_order.id + '&view_type=form&model=sale.order';
                        self.gui.show_popup('saleOrder', {'url':url, 'name':sale_order.name, 'edit': edit});

                    }
                    var record_exist = false;
                    _.each(self.get('pos_sale_order_list'), function(existing_order){
                        if(existing_order.id === sale_order.id){
                            _.extend(existing_order, sale_order);
                            record_exist = true;
                        }
                    });
                    if (!record_exist){
                        var exist = _.findWhere(self.get('pos_sale_order_list'), {id: sale_order.id});
                        if(!exist){
                            var defined_orders = self.get('pos_sale_order_list');
                            var new_orders = [sale_order].concat(defined_orders);
                            if(new_orders){
                                self.db.add_sale_orders(new_orders);
                                new_orders.map(function(new_order){
                                    if(new_order){
                                        var dt = new Date(new Date(new_order.date_order) + "GMT");
                                            var n = dt.toLocaleDateString();
                                            var crmon = self.addZero(dt.getMonth()+1);
                                            var crdate = self.addZero(dt.getDate());
                                            var cryear = dt.getFullYear();
                                            var crHour = self.addZero(dt.getHours());
                                            var crMinute = self.addZero(dt.getMinutes());
                                            var crSecond = self.addZero(dt.getSeconds());
                                         new_order.date_order = cryear + '/' + crmon +'/'+ crdate +' '+crHour +':'+ crMinute +':'+ crSecond;
                                    }
                                });
                                self.set({'pos_sale_order_list': new_orders})
                            }
                        }

                    }
                }
            }).catch(function(){
                if(paid){
                    $('#btn_so').show();
                }
            });
        },
        get_cashier: function(){
            return this.db.get_cashier() || this.get('cashier') || this.user;
        },
        set_cashier: function(employee){
            var self = this;
            var domain_order = [];
            posmodel_super.set_cashier.apply(this, arguments);
            if(employee){
                if(self.config.orders_sync && self.config.enable_reorder){
                    var from_date = moment().locale('en').format('YYYY-MM-DD')
                    if(self.config.last_days){
                        from_date = moment().subtract(self.config.last_days, 'days').locale('en').format('YYYY-MM-DD');
                    }
                    var domain_order = [];
                    var user_ids = [];
                    if(employee.pos_user_type=="salesman"){
                        domain_order.push(['salesman_id', '=', employee.id]);
                    } else if(employee.pos_user_type=="cashier") {
                        if(employee.sales_persons && employee.sales_persons.length > 0){
                           var selected_users = employee.sales_persons;
                           _.each(selected_users, function(each_user_id){
                                user_ids.push(each_user_id)
                           });
                           user_ids.push(employee.id);
                           domain_order.push('|',['salesman_id','=',false],['salesman_id', 'in', user_ids]);
                        } else {
                            domain_order.push(['salesman_id', '=', employee.id]);
                        }
                    }
                    if(self.config.enable_multi_store && self.pos_session.store_id && self.pos_session.store_id[0]){
                        domain_order.push('|',['store_id','=',false],['store_id','=',self.pos_session.store_id[0]],['state','not in',['cancel']], ['create_date', '>=', from_date]);
                    } else{
                        domain_order.push(['state','not in',['cancel']], ['create_date', '>=', from_date]);
                    }
                    var params = {
                        model: 'pos.order',
                        method: 'search_read',
                        domain: domain_order,
                    }
                    rpc.query(params, {async: false}).then(function(orders){
                        self.db.add_orders(orders);
                        self.set({'pos_order_list' : orders});
                        self.chrome.render_sale_note_order_list(orders);
                    });
                } else if(self.config.enable_print_last_receipt){
                    var params = {
                        model: 'pos.order',
                        method: 'search_read'
                    }
                    rpc.query(params, {async: false}).then(function(orders){
                        if(orders.length > 0){
                            self.db.add_orders(orders);
                            self.set({'pos_order_list' : orders});
                        }
                    }).catch(function(){
                        self.db.notification('danger',"Connection lost");
                    });
                }else if((self.config.enable_reorder && !self.config.orders_sync) || self.config.enable_credit){
                    var from_date = moment().locale('en').format('YYYY-MM-DD')
                    if(self.config.last_days){
                        from_date = moment().subtract(self.config.last_days, 'days').locale('en').locale('en').format('YYYY-MM-DD');
                    }
                    if(self.config.enable_multi_store && self.pos_session.store_id[0]){
                        self.domain_as_args = ['|',['store_id','=',false],['store_id','=',self.pos_session.store_id[0]],['state','not in',['cancel']], ['create_date', '>=', from_date]];
                    } else{
                        self.domain_as_args = [['state','not in',['cancel']], ['create_date', '>=', from_date]];
                    }
                    var params = {
                        model: 'pos.order',
                        method: 'ac_pos_search_read',
                        args: [{'domain': self.domain_as_args}],
                    }
                    rpc.query(params, {async: false}).then(function(orders){
                        if(orders.length > 0){
                            self.db.add_orders(orders);
                            self.set({'pos_order_list' : orders});
                        }
                    }).catch(function(){
                        self.db.notification('danger',"Connection lost");
                    });
                }
                if(employee.pos_user_type == "cashier"){
                    var button_clock = QWeb.render('SaleNoteIconChrome',{widget: self,user:employee});
                    var draft_orders = []
                    $('.sale_note_icon_widget').html(button_clock);
                    var orders = self.get('pos_order_list');
                    draft_orders = _.filter(orders, function(item) {
                         return item.state == 'draft'
                    });
                    $('.notification-count').show();
                    $('.draft_order_count').text(draft_orders.length);
                } else{
                    $('.sale_note_icon_widget').html("");
                }
            }

            if(employee && employee.user_id){
                var LockPromise =  new Promise(function(resolve, reject){
                    var params = {
                        model: 'pos.session',
                        method: 'write',
                        args: [self.pos_session.id,{'current_cashier_id':employee.user_id[0]}],
                    }
                    rpc.query(params, {async: false}).then(function(result){
                        if(result){
                            resolve(result);
                        }
                    }).catch(function(){
                        reject(self.db.notification('danger',"Connection lost"));
                    });
                })
                LockPromise.then(function(result){
                    if(employee && employee.lock_terminal){
                        var button_lock = QWeb.render('LockIconChrome',{widget: self});
                        $('.lock_widget').html(button_lock);
                    } else{
                        $('.lock_widget').html("");
                    }
                });
            }

            var delivery_orders = _.filter(self.get('pos_order_list'), function(item) {
                 return item.delivery_type == 'pending'
            });
            $('.delivery_order_count').text(delivery_orders.length);
        },
        get_customer_due: function(partner){
            var self = this;
            var domain = [];
            var amount_due = 0;
            domain.push(['partner_id', '=', partner.id],['reserved','=',false]);
            var params = {
                model: 'pos.order',
                method: 'search_read',
                domain: domain,
            }
            rpc.query(params, {async: false})
            .then(function(orders){
                if(orders){
                    var filtered_orders = orders.filter(function(o){return (o.amount_total - o.amount_paid) > 0})
                    for(var i = 0; i < filtered_orders.length; i++){
                        amount_due = amount_due + filtered_orders[i].amount_due;
                    }
                }
            })
            return amount_due;
        },
        start_timer: function(){
            var self = this;
            setInterval(function() {
                if(self.get_lock_status()){
                    if(self.get_lock_data() && self.get_lock_data().session_id[0] == self.pos_session.id){
                        $('#block_session_freeze_screen').addClass("active_state_freeze_screen");
                        $('.lock_screen_button').fadeIn(2000);
                        $('span.lock_screen_button').show();
                        $('#msg_lock').show();
                        $('#msg_lock').text("Your session has been blocked by "+self.get_lock_data().locked_by_user_id[1]);
                    } else{
                        $('#block_session_freeze_screen').removeClass("active_state_freeze_screen");
                        $('span.lock_screen_button').hide();
                        $('#msg_lock').hide();
                        $('#msg_lock').text('');
                    }
                } else{
                    $('#block_session_freeze_screen').removeClass("active_state_freeze_screen");
                    $('span.lock_screen_button').hide();
                    $('#msg_lock').hide();
                    $('#msg_lock').text('');
                }
            },2 * 1000);
        },
        set_lock_status:function(status){
            this.set('pos_block_status',status)
        },
        get_lock_status: function(){
            return this.get('pos_block_status')
        },
        set_lock_data: function(lock_data){
            this.set('pos_block_data',lock_data);
        },
        get_lock_data: function(){
            return this.get('pos_block_data');
        },
        /*_save_to_server: function (orders, options) {
            var self = this;
            return posmodel_super._save_to_server.apply(this, arguments)
            .then(function(server_ids){
                _.each(orders, function(order) {
                    var lines = order.data.lines;
                    _.each(lines, function(line){
                        if(line[2].location_id === self.config.stock_location_id[0]){
                            if(order.data.amount_due <= 0 || order.data.order_make_picking){
                                var product_id = line[2].product_id;
                                var product_qty = line[2].qty;
                                var product = self.db.get_product_by_id(product_id);
                                var remain_qty = product.qty_available - product_qty;
                                product.qty_available = remain_qty;
                                self.gui.screen_instances.products.product_list_widget.product_cache.clear_node(product.id)
                                var prod_obj = self.gui.screen_instances.products.product_list_widget;
                                var current_pricelist = prod_obj._get_active_pricelist();
                                if(current_pricelist){
                                    prod_obj.product_cache.clear_node(product.id+','+current_pricelist.id);
                                    prod_obj.render_product(product);
                                }
                                prod_obj.renderElement();
                            }
                        }
                    });
                });
                if(server_ids.length > 0){
                    $.ajax({
                        type: "GET",
                        url: '/web/dataset/send_pos_ordermail',
                        data: {
                            order_ids: JSON.stringify(server_ids),
                        },
                        success: function(res) {},
                        error: function() {self.db.notification('danger',"Mail Not send.");},
                    });
                }
                if(server_ids.length > 0 && self.config.enable_reorder){
                    var domain_list;
                    if(self.config.multi_store_id && self.config.multi_store_id[0]){
                        domain_list = ['|',['store_id','=',false],['store_id','=',self.config.multi_store_id[0]],['id','in',server_ids]]
                    } else{
                        domain_list = [['id','in',server_ids],['store_id','=',false]]
                    }
                    var params = {
                        model: 'pos.order',
                        method: 'ac_pos_search_read',
                        args: [{'domain': domain_list}],
                    }
                    rpc.query(params, {async: false}).then(function(orders){
                        if(orders.length > 0){
                            orders = orders[0];
                            var exist_order = _.findWhere(self.get('pos_order_list'), {'pos_reference': orders.pos_reference})
                            if(exist_order){
                                _.extend(exist_order, orders);
                            } else {
                                self.get('pos_order_list').push(orders);
                            }
                            var new_orders = _.sortBy(self.get('pos_order_list'), 'id').reverse();
                            self.db.add_orders(new_orders);
                            self.set({ 'pos_order_list' : new_orders });
                            self.chrome.render_sale_note_order_list(new_orders);
                        }
                    }).catch(function(){
                        self.db.notification('danger',"Connection lost");
                    });
                }
            });
        },*/
//		send_new_notif: function(){
//			this.get_order().mirror_image_data();
//		},
        // change the current order
        set_order: function(order){
            this.set({ selectedOrder: order });
            var selectedOrder = this.get_order();
            if(selectedOrder && selectedOrder.get_reservation_mode()){
                selectedOrder.change_mode("reservation_mode");
            } else {
                if(selectedOrder){
                    selectedOrder.change_mode("sale");
                }
            }
        },
        zero_pad: function(num, size){
            var s = ""+num;
            while (s.length < size) {
                s = "0" + s;
            }
            return s;
        },
        add_new_order: function(){
            var self = this;
            $('#open_calendar').css({'background-color':''});
            $('#delivery_mode').removeClass('deliver_on');
            var order = this.get_order();
            if(self.config.vertical_categories) {
                if(self.chrome.screens){
                    var start_categ_id = self.chrome.screens.products.product_categories_widget.start_categ_id;
                    if(start_categ_id){
                        var categ = self.db.get_category_by_id(start_categ_id);
                        if(categ.parent_id.length > 0){
                            self.chrome.screens.products.set_back_to_parent_categ(categ.parent_id[0]);
                            $(".v-category[data-category-id='"+start_categ_id+"']").trigger('click');
                        }else{
                            var sub_categories = self.db.get_category_by_id(self.db.get_category_childs_ids(0));
                            self.chrome.screens.products.render_product_category(sub_categories);
                            $(".v-category[data-category-id='"+start_categ_id+"']").trigger('click');
                        }
                    }else{
                        var sub_categories = self.db.get_category_by_id(self.db.get_category_childs_ids(0));
                        self.chrome.screens.products.render_product_category(sub_categories);
                        $(".v-category[data-category-id='0']").trigger('click');
                    }
                }
            }
            return posmodel_super.add_new_order.apply(this);
        },
        set_locked_user: function(locked_user){
            this.locked_user = locked_user;
        },
        get_locked_user: function(){
            return this.locked_user;
        },
        set_locked_screen: function(locked_screen){
            this.locked_screen = locked_screen;
        },
        get_locked_screen: function(){
            return this.locked_screen;
        },
        set_login_from: function(login_from){
            this.login_from = login_from;
        },
        get_login_from: function(){
            return this.login_from;
        },
        delete_current_order: function(){
            var self = this;
            posmodel_super.delete_current_order.apply(this);
            $('#wrapper1').addClass('toggled');
            $('#slidemenubtn1').css({'right':'0px'});
            $('.product-list-container').css('width','100%');
        },
    });

    var _super_Order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function(attributes,options){
            // if(options.json){
            // 	options.json.lines = [];
            // 	options.json.statement_ids = [];
            // }
            this.serial_list = [];
            this.print_serial = true;
            var res = _super_Order.initialize.apply(this, arguments);
            this.set({
                paying_order: false,
                type_for_credit: false,
                change_amount_for_credit: false,
                use_credit: false,
                order_make_picking: false,
                credit_detail: [],
                customer_credit:false,
                ret_o_id: null,
                ret_o_ref: null,
                sale_mode: true,
                missing_mode: false,
                loyalty_redeemed_point: Number(0.00),
                loyalty_earned_point: 0.00,
                type_for_wallet: false,
                change_amount_for_wallet: 0.00,
                use_wallet: false,
                used_amount_from_wallet: false,
                //Reservartion
                reservation_mode: false,
                reserve_delivery_date: false,
                draft_order: false,
                paying_due: false,
                fresh_order: false,
                sale_order_name: false,
                invoice_name: false,
                order_id: false,
                shipping_address: false,
                invoice_address: false,
                sale_note: false,
                signature: false,
                inv_id: false,
                sale_order_date: false,
                edit_quotation: false,
                paying_sale_order: false,
                sale_order_pay: false,
                invoice_pay: false,
                sale_order_requested_date: false,
                invoice_id:false,
                delivery_mode:false,
                custom_uom_id:false,
            });
            $("div#sale_mode").addClass('selected-menu');
            $("div#order_return").removeClass('selected-menu');
            $("div#reservation_mode").removeClass('selected-menu');
            $("div#sale_order_mode").removeClass('selected-menu');
            this.receipt_type = 'receipt';  // 'receipt' || 'invoice'
            this.temporary = options.temporary || false;
            this.rounding_status = false;
            this.giftcard = [];
            this.redeem =[];
            this.recharge=[];
            this.date=[];
            this.voucher = [];
            this.remaining_redeemption = false;
            this.is_categ_sideber_open = false;
            this.delivery_user_id = false;
            this.is_kitchen_order = false;
            return this;
        },
        // set_sale_order_pay: function(so_pay_mode){
        // 	this.so_pay_mode = so_pay_mode;
        // },
        // get_sale_order_pay: function(){
        // 	return this.so_pay_mode;
        // },
        is_kitchen_order: function(is_kitchen_order) {
            this.is_kitchen_order = is_kitchen_order;
        },
        get_is_kitchen_order: function(){
            return this.is_kitchen_order;
        },
        set_is_update_increnement_number: function(is_update_increnement_number) {
            this.is_update_increnement_number = is_update_increnement_number;
        },
        get_is_update_increnement_number: function() {
            return this.is_update_increnement_number;
        },
        set_temp_increment_number: function(temp_increment_number){
            this.temp_increment_number = temp_increment_number;
        },
        get_temp_increment_number: function(){
            return this.temp_increment_number;
        },
        set_is_debit: function(is_debit) {
            this.set('is_debit',is_debit);
        },
        get_is_debit: function(){
            return this.get('is_debit');
        },
        set_change_amount_for_credit: function(change_amount_for_credit) {
            this.set('change_amount_for_credit', change_amount_for_credit);
        },
        get_change_amount_for_credit: function() {
            return this.get('change_amount_for_credit');
        },
        set_change_and_cash: function(change_and_cash) {
            this.change_and_cash = change_and_cash;
        },
        get_change_and_cash: function() {
            return this.change_and_cash;
        },
        set_credit_mode: function(credit_mode) {
            this.credit_mode = credit_mode;
        },
        get_credit_mode: function() {
            return this.credit_mode;
        },
        set_credit_detail: function(credit_detail) {
            var data = this.get('credit_detail')
            data.push(credit_detail);
            this.set('credit_detail',data);
        },
        get_credit_detail: function() {
            return this.get('credit_detail')
        },
        set_customer_credit:function(){
            var data = this.get('customer_credit')
            data = true;
            this.set('customer_credit',data);
        },
        get_customer_credit: function() {
            return this.get('customer_credit')
        },
        set_last_order_print: function (ref) {
            this.last_order_print = ref;
        },
        get_last_order_print: function () {
            return this.last_order_print;
        },
        set_order_make_picking: function(order_make_picking) {
            this.set('order_make_picking', order_make_picking);
        },
        get_order_make_picking: function() {
            return this.get('order_make_picking');
        },
        set_sale_order_name: function(name){
            this.set('sale_order_name', name);
        },
        get_sale_order_name: function(){
            return this.get('sale_order_name');
        },
        set_invoice_name: function(name){
            this.set('invoice_name', name);
        },
        get_invoice_name: function(){
            return this.get('invoice_name');
        },
        set_shipping_address: function(val){
            this.set('shipping_address', val);
        },
        get_shipping_address: function() {
            return this.get('shipping_address');
        },
        set_invoice_address: function(val){
            this.set('invoice_address', val);
        },
        get_invoice_address: function() {
            return this.get('invoice_address');
        },
        set_sale_note: function(val){
            this.set('sale_note', val);
        },
        get_sale_note: function() {
            return this.get('sale_note');
        },
        set_signature: function(signature) {
            this.set('signature', signature);
        },
        get_signature: function() {
            return this.get('signature');
        },
        set_inv_id: function(inv_id) {
            this.set('inv_id', inv_id)
        },
        get_inv_id: function() {
            return this.get('inv_id');
        },
        set_sale_order_date: function(sale_order_date) {
            this.set('sale_order_date', sale_order_date)
        },
        get_sale_order_date: function() {
            return this.get('sale_order_date');
        },
        set_sale_order_requested_date: function(sale_order_requested_date) {
            this.set('sale_order_requested_date', sale_order_requested_date)
        },
        get_sale_order_requested_date: function() {
            return this.get('sale_order_requested_date');
        },
        set_edit_quotation: function(edit_quotation) {
            this.set('edit_quotation', edit_quotation)
        },
        get_edit_quotation: function() {
            return this.get('edit_quotation');
        },
        set_paying_sale_order: function(paying_sale_order) {
            this.set('paying_sale_order', paying_sale_order)
        },
        get_paying_sale_order: function() {
            return this.get('paying_sale_order');
        },
        set_sale_order_pay: function(sale_order_pay) {
            this.set('sale_order_pay', sale_order_pay)
        },
        get_sale_order_pay: function() {
            return this.get('sale_order_pay');
        },
        set_invoice_id: function(invoice_id) {
            this.set('invoice_id', invoice_id)
        },
        get_invoice_id: function() {
            return this.get('invoice_id');
        },
        set_invoice_pay: function(invoice_pay) {
            this.set('invoice_pay', invoice_pay)
        },
        get_invoice_pay: function() {
            return this.get('invoice_pay');
        },
        set_result_expire_graph: function(result) {
            this.set('result', result);
        },
        get_result_expire_graph: function() {
            return this.get('result');
        },
        set_graph_data_journal: function(result) {
            this.set('result_graph_data_journal', result);
        },
        get_graph_data_journal: function() {
            return this.get('result_graph_data_journal');
        },
        set_active_session_sales: function(active_session_sale){
            this.set('active_session_sale',active_session_sale)
        },
        get_active_session_sales: function(){
            return this.get('active_session_sale');
        },
        set_closed_session_sales: function(closed_session_sale){
            this.set('closed_session_sale',closed_session_sale)
        },
        get_closed_session_sales: function(){
            return this.get('closed_session_sale');
        },
        set_hourly_summary: function(hourly_summary){
            this.set('hourly_summary',hourly_summary)
        },
        get_hourly_summary: function(){
            return this.get('hourly_summary');
        },
        set_month_summary: function(month_summary){
            this.set('month_summary',month_summary);
        },
        get_month_summary: function(){
            return this.get('month_summary');
        },
        set_six_month_summary: function(six_month_summary){
            this.set('last_six_month_sale',six_month_summary);
        },
        get_six_month_summary: function(){
            return this.get('last_six_month_sale');
        },
        set_customer_summary: function(customer_summary){
            this.set('customer_summary',customer_summary);
        },
        get_customer_summary: function(){
            return this.get('customer_summary');
        },
        set_top_product_result: function(top_products){
            this.set('top_product',top_products);
        },
        get_top_product_result: function(){
            return this.get('top_product');
        },
      //Out of Stock
        set_receipt_mode: function(receipt_mode) {
            this.receipt_mode = receipt_mode;
        },
        get_receipt_mode: function() {
            return this.receipt_mode;
        },
        set_product_vals :function(product_vals) {
            this.product_vals = product_vals;
        },
        get_product_vals: function() {
            return this.product_vals;
        },
        set_location_vals: function(select_location) {
            this.select_location = select_location;
        },
        get_location_vals: function() {
            return this.select_location;
        },
        set_list_products: function(list_products){
            this.list_products = list_products;
        },
        get_list_products: function(){
            return this.list_products;
        },
//        Cash In/Out
        set_money_inout_details: function(money_inout_details){
            this.money_inout_details = money_inout_details;
        },
        get_money_inout_details: function(){
            return this.money_inout_details;
        },
        set_cash_register: function(result){
            this.result = result;
        },
        get_cash_register: function(){
            return this.result;
        },
        set_statement_cashier: function(user_id){
            this.user_id = user_id;
        },
        get_statement_cashier: function(){
            return this.user_id;
        },
        //Reservation
        set_reservation_mode: function(mode){
            this.set('reservation_mode', mode)
        },
        get_reservation_mode: function(){
            return this.get('reservation_mode');
        },
        set_reserve_delivery_date: function(val){
            this.set('reserve_delivery_date', val)
        },
        get_reserve_delivery_date: function(){
            return this.get('reserve_delivery_date');
        },
        set_cancel_order: function(val){
            this.set('cancel_order', val)
        },
        get_cancel_order: function(){
            return this.get('cancel_order');
        },
        set_paying_due: function(val){
            this.set('paying_due', val)
        },
        get_paying_due: function(){
            return this.get('paying_due');
        },
        set_draft_order: function(val) {
            this.set('draft_order', val);
        },
        get_draft_order: function() {
            return this.get('draft_order');
        },
        set_cancellation_charges: function(val) {
            this.set('cancellation_charges', val);
        },
        get_cancellation_charges: function() {
            return this.get('cancellation_charges');
        },
        set_refund_amount: function(refund_amount) {
            this.set('refund_amount', refund_amount);
        },
        get_refund_amount: function() {
            return this.get('refund_amount');
        },
        set_fresh_order: function(fresh_order) {
            this.set('fresh_order', fresh_order);
        },
        get_fresh_order: function() {
            return this.get('fresh_order');
        },
        set_partial_pay: function(partial_pay) {
            this.set('partial_pay', partial_pay);
        },
        get_partial_pay: function() {
            return this.get('partial_pay');
        },
        set_merge_table_ids: function(table_ids){
            this.set('table_ids',table_ids);
        },
        get_merge_table_ids: function(){
            return this.get('table_ids');
        },
        // end reservation
        is_sale_product: function(product){
            var self = this;
            var delivery_product_id = self.pos.config.delivery_product_id[0] || false;
            if(product.is_packaging){
                return false;
            } else if(product.id == delivery_product_id){
                return false;
            }else {
                return true;
            }
        },
        set_is_categ_sideber_open: function(is_categ_sideber_open){
            this.is_categ_sideber_open = is_categ_sideber_open;
        },
        get_is_categ_sideber_open: function(){
            return this.is_categ_sideber_open;
        },
        empty_cart: function(){
            var self = this;
            var currentOrderLines = this.get_orderlines();
            var lines_ids = []
            if(!this.is_empty()) {
                _.each(currentOrderLines,function(item) {
                    lines_ids.push(item.id);
                });
                _.each(lines_ids,function(id) {
                    self.remove_orderline(self.get_orderline(id));
                });
            }
        },
        change_mode: function(mode){

            if(mode == 'sale'){
                //Enable mode
                this.set_sale_mode(true);
                $("div#sale_mode").addClass('selected-menu');

                //disable other modes
                this.set_missing_mode(false);
                this.set_reservation_mode(false);
                this.set_sale_order_mode(false);
                $("div#order_return").removeClass('selected-menu');
                $("div#reservation_mode").removeClass('selected-menu');
                $("div#sale_order_mode").removeClass('selected-menu');
            } else if( mode == 'missing') {
                if(this.get_is_delivery()){
                    self.pos.db.notification('danger',_t('Sorry, Delivery only allow with Sale Mode!'));
                    this.set_sale_mode(true);
                    $("div#sale_mode").addClass('selected-menu');
                    return
                }
                //Enable mode
                this.set_missing_mode(true);
                $("div#order_return").addClass('selected-menu');
                //disable other modes
                this.set_sale_mode(false);
                this.set_reservation_mode(false);
                this.set_sale_order_mode(false);
                this.set_is_delivery(false);
                this.set_order_total_discount(0.00);
                this.set_loyalty_earned_point(0);
                this.set_loyalty_earned_amount(0.00);

                $("div#sale_mode").removeClass('selected-menu');
                $("div#reservation_mode").removeClass('selected-menu');
                $("div#sale_order_mode").removeClass('selected-menu');
                $('#delivery_mode').removeClass('deliver_on')
            } else if(mode == 'reservation_mode'){
                if(this.get_is_delivery()){
                    self.pos.db.notification('danger',_t('Sorry, Delivery only allow with Sale Mode!'));
                    this.set_sale_mode(true);
                    $("div#sale_mode").addClass('selected-menu');
                    return
                }
                //Enable mode
                this.set_reservation_mode(true);
                $("div#reservation_mode").addClass('selected-menu');

                //disable other modes
                this.set_sale_mode(false);
                this.set_is_delivery(false);
                this.set_missing_mode(false);
                this.set_sale_order_mode(false);
                this.set_order_total_discount(0.00);
                this.set_loyalty_earned_point(0);
                this.set_loyalty_earned_amount(0.00);
                $("div#sale_mode").removeClass('selected-menu');
                $("div#order_return").removeClass('selected-menu');
                $("div#sale_order_mode").removeClass('selected-menu');
                $('#delivery_mode').removeClass('deliver_on')
            } else if(mode == 'sale_order_mode'){
                if(this.get_is_delivery()){
                    self.pos.db.notification('danger',_t('Sorry, Delivery only allow with Sale Mode!'));
                    this.set_sale_mode(true);
                    $("div#sale_mode").addClass('selected-menu');
                    return
                }
                this.set_sale_order_mode(true);
                $("div#sale_order_mode").addClass('selected-menu');

                //disable other modes
                this.set_sale_mode(false);
                this.set_is_delivery(false);
                this.set_missing_mode(false);
                this.set_reservation_mode(false);
                this.set_order_total_discount(0.00);
                this.set_loyalty_earned_point(0);
                this.set_loyalty_earned_amount(0.00);
                $("div#sale_mode").removeClass('selected-menu');
                $("div#reservation_mode").removeClass('selected-menu');
                $("div#order_return").removeClass('selected-menu');
                $('#delivery_mode').removeClass('deliver_on')
            } else if(mode == 'delivery_mode'){
                var order = self.pos.get_order();
                //disable other modes
                this.set_sale_order_mode(false);
                this.set_missing_mode(false);
                this.set_reservation_mode(false);
                $("div#reservation_mode").removeClass('selected-menu');
                $("div#order_return").removeClass('selected-menu');
                $("div#sale_order_mode").removeClass('selected-menu');
                var lines = order.get_orderlines();
                var line = order.get_selected_orderline();
                if(!order.get_sale_mode()){
                    self.pos.db.notification('danger',_t('Sorry, This operation only allow with Sale Mode!'));
                    this.set_sale_mode(true);
                    $("div#sale_mode").addClass('selected-menu');
                    return
                }
                // var selected_orderline = (line && line.get_quantity() > 0 && order.is_sale_product(line.product)) ? line : false;
                // if(order.get_ret_o_id()){
                // 	self.pos.db.notification('danger',_t('Sorry, This operation not allow to use delivery operation!'));
                // 	return
                // }
                if($('#delivery_mode').hasClass('deliver_on')){
                    if(lines.length > 0){
                        self.gui.show_popup('confirm',{
                            'title': _t('Delivery Order?'),
                            'body':  _t('You want to remove delivery order?'),
                            confirm: function(){
//                            	order.clear_cart();
                                order.set_is_delivery(false);
                                lines.map(function(line){
                                    line.set_deliver_info(false);
                                    if(line.get_delivery_charges_flag()){
                                        order.remove_orderline(line);
                                    }
                                });
                                $('#delivery_mode').removeClass('deliver_on');
                            },
                        });
                    }
                }else{
                    if(lines.length > 0){
                        self.gui.show_popup('confirm',{
                            'title': _t('Delivery Order?'),
                            'body':  _t('You want to make delivery order?'),
                            confirm: function() {
                                if (!order.get_is_delivery()) {
                                    var deliver_product_id = self.pos.config.delivery_product_id[0];
                                    var deliver_amt = self.pos.config.delivery_amount;
                                    var product = self.pos.db.get_product_by_id(deliver_product_id);
                                    if (product) {
                                        var line_deliver_charges = new models.Orderline({}, {
                                            pos: self.pos,
                                            order: order,
                                            product: product
                                        });
                                        line_deliver_charges.set_quantity(1);
                                        line_deliver_charges.set_unit_price(deliver_amt || 0);
                                        line_deliver_charges.set_delivery_charges_color(true);
                                        line_deliver_charges.set_delivery_charges_flag(true);
                                        line_deliver_charges.state = 'done';
                                        order.add_orderline(line_deliver_charges);
                                        order.set_is_delivery(true);
                                        lines.map(function (line) {
                                            line.set_deliver_info(true);
                                        });
                                        order.set_delivery(true);
                                        order.mirror_image_data();
                                        $('#delivery_mode').addClass('deliver_on');
                                    }
                                }
                            }
                        });
                    }
                }
            }
        },
        set_pricelist: function (pricelist) {
            var self = this;
            this.pricelist = pricelist;
            if(pricelist != self.pos.default_pricelist && self.pos.config.use_pricelist){
                _.each(this.get_orderlines(), function (line) {
                    line.set_original_price(line.get_display_price());
                });
            }
            var lines_to_recompute = _.filter(this.get_orderlines(), function (line) {
                return ! line.price_manually_set;
            });
            _.each(lines_to_recompute, function (line) {
                if(!line.product.is_dummy_product && !line.get_is_rule_applied()){
                    line.set_unit_price(line.product.get_price(self.pricelist, line.get_quantity()));
                    self.fix_tax_included_price(line);
                }
            });
            this.trigger('change');
        },
        set_sale_order_mode: function(sale_order_mode){
            this.sale_order_mode = sale_order_mode;
        },
        get_sale_order_mode: function(){
            return this.sale_order_mode;
        },
        set_reserved_order: function(reseved_mode){
            this.reseved_mode = reseved_mode;
        },
        get_reserved_order : function(){
            return this.reseved_mode;
        },
        set_sale_mode: function(sale_mode) {
            this.set('sale_mode', sale_mode);
        },
        get_sale_mode: function() {
            return this.get('sale_mode');
        },
        set_missing_mode: function(missing_mode) {
            this.set('missing_mode', missing_mode);
        },
        get_missing_mode: function() {
            return this.get('missing_mode');
        },
        generate_unique_id: function() {
            var timestamp = new Date().getTime();
            return Number(timestamp.toString().slice(-10));
        },
        generateUniqueId_barcode: function() {
            return new Date().getTime();
        },
        set_ereceipt_mail: function(ereceipt_mail) {
            this.set('ereceipt_mail', ereceipt_mail);
        },
        get_ereceipt_mail: function() {
            return this.get('ereceipt_mail');
        },
        set_prefer_ereceipt: function(prefer_ereceipt) {
            this.set('prefer_ereceipt', prefer_ereceipt);
        },
        get_prefer_ereceipt: function() {
            return this.get('prefer_ereceipt');
        },
        set_order_note: function(order_note) {
            this.order_note = order_note;
        },
        get_order_note: function() {
            return this.order_note;
        },
        set_ret_o_id: function(ret_o_id) {
            this.set('ret_o_id', ret_o_id)
        },
        get_ret_o_id: function(){
            return this.get('ret_o_id');
        },
        set_ret_o_ref: function(ret_o_ref) {
            this.set('ret_o_ref', ret_o_ref)
        },
        get_ret_o_ref: function(){
            return this.get('ret_o_ref');
        },
//        Payment Summary
        set_sales_summary_mode: function(sales_summary_mode) {
            this.sales_summary_mode = sales_summary_mode;
        },
        get_sales_summary_mode: function() {
            return this.sales_summary_mode;
        },
        set_sales_summary_vals :function(sales_summary_vals) {
            this.sales_summary_vals = sales_summary_vals;
        },
        get_sales_summary_vals: function() {
            return this.sales_summary_vals;
        },
// Order Summary
        set_receipt: function(custom_receipt) {
            this.custom_receipt = custom_receipt;
        },
        get_receipt: function() {
            return this.custom_receipt;
        },
        set_order_list: function(order_list) {
            this.order_list = order_list;
        },
        get_order_list: function() {
            return this.order_list;
        },

        cart_product_qnty: function(product_id,flag){
            var self = this;
            var res = 0;
            var order = self.pos.get_order();
            var orderlines = order.get_orderlines();
            if (flag){
                _.each(orderlines, function(orderline){
                    if(orderline.product.id == product_id){
                        res += orderline.quantity
                    }
                });
                return res;
            } else {
                _.each(orderlines, function(orderline){
                    if(orderline.product.id == product_id && !orderline.selected){
                        res += orderline.quantity
                    }
                });
                return res;
            }
        },
        clear_cart: function(){
            var self = this;
            var order = self.pos.get_order();
            var currentOrderLines = order.get_orderlines();
            var lines_ids = []
            if(!order.is_empty()) {
                _.each(currentOrderLines,function(item) {
                    lines_ids.push(item.id);
                });
                _.each(lines_ids,function(id) {
                    order.remove_orderline(order.get_orderline(id));
                });
            }
        },
        get_product_qty: function(product_id){
            var self = this;
            var order = self.pos.get_order();
            var lines = order.get_new_order_lines();
            var new_lines = [];
            var line_ids = [];
            var qty = 0;
            _.each(lines, function(line){
                if(line && line.get_quantity() > 0 && !line.get_is_rule_applied()){
                    if(line.product.id == product_id){
                        qty += line.get_quantity();
                        line_ids.push(line.id);
                    }
                }
            });
            var result = {
                'total_qty':Number(qty),
                'line_ids':line_ids,
            }
            return result;
        },
        add_product: function(product, options){
            var self = this;
            if(this.get_missing_mode()){
                return _super_Order.add_product.call(this, product, {quantity:-1});
            } else if(options && options.force_allow){
                _super_Order.add_product.call(this, product, options);
            } else {
                var product_quaty = self.cart_product_qnty(product.id,true);
                if(self.pos.config.restrict_order && self.pos.get_cashier().access_show_qty && product.type != "service"){
                    if(self.pos.config.prod_qty_limit){
                        var remain = product.qty_available-self.pos.config.prod_qty_limit
                        if(product_quaty>=remain){
                            if(self.pos.config.custom_msg){
                                self.pos.db.notification('warning',self.pos.config.custom_msg);
                            } else{
                                self.pos.db.notification('warning', _t('Product Out of Stock'));
                            }
                            return
                        }
                    }
                    if(product_quaty>=product.qty_available && !self.pos.config.prod_qty_limit){
                        if(self.pos.config.custom_msg){
                            self.pos.db.notification('warning',self.pos.config.custom_msg);
                        } else{
                            self.pos.db.notification('warning', _t('Product Out of Stock'));
                        }
                        return
                    }
                }if(product && self.pos.prod_mrp_bom_data){
                    var bom_data =[];
                    var bom_line_by_id = self.pos.bom_line_by_id;
                     _.each(bom_line_by_id, function(item) {
                         if(item.parent_product_tmpl_id[0] == product.product_tmpl_id){
                            bom_data.push(item)
                         }
                    });

                    if(bom_data && bom_data[0]){
                        setTimeout(function(){
                            var order = self.pos.get_order();
                            var line_ref = Date.now() + ( (Math.random()*100000).toFixed());
                            var selected_line = order.get_selected_orderline();
                            selected_line.set_bom_line_at_start(bom_data);
                            selected_line.set_orderline_ref(line_ref);
                        },1000)
                    }
                } else {
                    self.pos.gui.screen_instances.products.hide_bom_widget();
                }
                _super_Order.add_product.call(this, product, options);
            }
            var selected_line = this.get_selected_orderline();
            if(selected_line && product.send_to_kitchen){
                if(product.priority){
                    selected_line.set_kitchen_item_priority(product.priority);
                }else{
                    selected_line.set_kitchen_item_priority('low');
                }
                self.pos.chrome.screens.products.order_widget.rerender_orderline(selected_line);
            }
            if(this.get_delivery() && $('#delivery_mode').hasClass('deliver_on')){
                selected_line.set_deliver_info(true);
            }
            if(selected_line && this.pricelist != this.pos.default_pricelist && this.pos.config.use_pricelist){
                selected_line.set_original_price(product.get_price(this.pos.default_pricelist, selected_line.get_quantity()))
            }
            self.remove_promotion();
            self.apply_promotion();
             if(self.pos.config.customer_display){
                self.mirror_image_data();
             }
            var return_valid_days = 0;
            if(self.pos.config.enable_print_valid_days){
                if(!product.non_refundable){
                    if(product.return_valid_days > 0){
                        return_valid_days = product.return_valid_days;
                    }else{
                        if(product.pos_categ_id && product.pos_categ_id[0]){
                            var categ = self.pos.db.category_by_id[product.pos_categ_id[0]];
                            if(categ.parent_id && categ.parent_id[0]){
                                while (categ.parent_id[0]) {
                                    categ = self.pos.db.category_by_id[categ.parent_id[0]];
                                    if(categ && categ.return_valid_days > 0){
                                        return_valid_days = categ.return_valid_days;
                                    }
                                }
                            } else{
                                if(categ){
                                    return_valid_days = categ.return_valid_days;
                                }
                            }
                        }
                    }
                }else{
                    return_valid_days = 0;
                }
            }
            selected_line.set_return_valid_days(return_valid_days);
            if(product.is_combo && product.product_combo_ids.length > 0 && self.pos.config.enable_combo && self.pos.user.access_combo){
                self.pos.gui.show_popup('combo_product_popup',{
                    'product':product
                });
            }
        },
        set_client: function(client){
            if(this.get_sale_order_name()){
                return
            }
            _super_Order.set_client.apply(this, arguments);
            if(this.pos.gui.get_current_screen() == 'products'){
                if(client){
                    $('.c-user').text(client.name);
                     var img_src = "<img style='height:50px;width:50px' src='/web/image?model=res.partner&id="+client.id+"&field=image_small'/>";
                     $('span.avatar-img').html(img_src);
                }else{
                     var img_src = "<i style='font-size:50px;padding: 8px;' class='fa fa-user' aria-hidden='true'></i>";
                     $('span.avatar-img').html(img_src);
                    $('.c-user').text('Guest Customer');
                }
            }

            this.mirror_image_data();
        },
        mirror_image_data:function(neworder){
            var self = this;
            var client_name = false;
            var order_total = self.getNetTotalTaxIncluded();
            var change_amount = self.get_change();
            var payment_info = [];
            var paymentlines = self.paymentlines.models;
            if(paymentlines && paymentlines[0]){
                paymentlines.map(function(paymentline){
                    payment_info.push({
                        'name':paymentline.name,
                        'amount':paymentline.amount,
                    });
                });
            }
            if(self.get_client()){
                client_name = self.get_client().name;
            }
            var vals = {
                'cart_data':$('.order-container').html(),
                'client_name':client_name,
                'order_total':order_total,
                'change_amount':change_amount,
                'payment_info':payment_info,
                'enable_customer_rating':self.pos.config.enable_customer_rating,
                'set_customer':self.pos.config.set_customer,
            }
            if(neworder){
                vals['new_order'] = true;
            }
            rpc.query({
                model: 'customer.display',
                method: 'broadcast_data',
                args: [vals],
            })
            .then(function(result) {});
        },       
        set_rating: function(rating){
            this.rating = rating;
        },
        get_rating: function(){
            return this.rating;
        },
        remove_promotion: function(){
            var self = this;
            var order = self.pos.get_order();
            var lines = order.get_orderlines();
            var selected_line = order.get_selected_orderline() || false;
            var cashier = self.pos.get_cashier();
            lines.map(function(selected_line){
                if(selected_line){
                    if(selected_line.get_child_line_id()){
                        var child_line = order.get_orderline(selected_line.get_child_line_id());
                        if(child_line){
                            selected_line.set_child_line_id(false);
                            selected_line.set_is_rule_applied(false);
                            order.remove_orderline(child_line);
                        }
                    }else if(selected_line.get_buy_x_get_dis_y()){
    //					if(selected_line.get_quantity() < 1){
                            _.each(lines, function(line){
                                if(line && line.get_buy_x_get_y_child_item()){
                                    line.set_discount(0);
                                    line.set_buy_x_get_y_child_item({});
                                    line.set_promotion_data("");
                                    line.set_is_rule_applied(false);
                                    self.pos.chrome.screens.products.order_widget.rerender_orderline(line);
                                }
                            });
    //					}
                    }else if(selected_line.get_quantity_discount()){
                        selected_line.set_quantity_discount({});
                        selected_line.set_promotion_data("");
                        selected_line.set_discount(0);
                        selected_line.set_is_rule_applied(false);
                    }else if(selected_line.get_discount_amt()){
                        selected_line.set_discount_amt_rule(false);
                        selected_line.set_promotion_data("");
                        selected_line.set_discount_amt(0);
                        selected_line.set_unit_price(selected_line.product.list_price);
                        selected_line.set_is_rule_applied(false);
                    }
                    else if(selected_line.get_multi_prods_line_id()){
                        var multi_prod_id = selected_line.get_multi_prods_line_id() || false;
                        if(multi_prod_id){
                            _.each(lines, function(_line){
                                if(_line && _line.get_multi_prods_line_id() == multi_prod_id){
                                    _line.set_discount(0);
                                    _line.set_is_rule_applied(false);
                                    _line.set_promotion_data(false);
                                    _line.set_combinational_product_rule(false);
                                    self.pos.chrome.screens.products.order_widget.rerender_orderline(_line);
                                }
                            });
                        }
                    }
                }
            });
        },
        apply_promotion: function(){
            var self = this;
            if(!self.pos.config.pos_promotion || !self.pos.get_cashier().access_pos_promotion){
                return;
            }
            self.remove_promotion();
            var order = self.pos.get_order();
            var lines = order.get_new_order_lines();
            var promotion_list = self.pos.pos_promotions;
            var condition_list = self.pos.pos_conditions;
            var discount_list = self.pos.pos_get_discount;
            var pos_get_qty_discount_list = self.pos.pos_get_qty_discount;
            var pos_qty_discount_amt = self.pos.pos_qty_discount_amt;
            var pos_discount_multi_prods = self.pos.pos_discount_multi_prods;
            var pos_discount_multi_categ = self.pos.pos_discount_multi_categ;
            var pos_discount_above_price = self.pos.pos_discount_above_price;
            var selected_line = self.pos.get_order().get_selected_orderline();
            var current_time = Number(moment(new Date().getTime()).locale('en').format("H"));
            if(order && lines && lines[0]){
                _.each(lines, function(line){
                    if(promotion_list && promotion_list[0]){
                        _.each(promotion_list, function(promotion){
                            if((Number(promotion.from_time) <= current_time && Number(promotion.to_time) > current_time) || (!promotion.from_time && !promotion.to_time)){
                                if(promotion && promotion.promotion_type == "buy_x_get_y"){
                                    if(promotion.pos_condition_ids && promotion.pos_condition_ids[0]){
                                        _.each(promotion.pos_condition_ids, function(pos_condition_line_id){
                                            var line_record = _.find(condition_list, function(obj) { return obj.id == pos_condition_line_id});
                                            if(line_record){
                                                if(line_record.product_x_id && line_record.product_x_id[0] == line.product.id){
                                                    if(line_record.operator == 'is_eql_to'){
                                                        if(line_record.quantity == line.quantity){
                                                            if(line_record.product_y_id && line_record.product_y_id[0]){
                                                                var product = self.pos.db.get_product_by_id(line_record.product_y_id[0]);
                                                                var new_line = new models.Orderline({}, {pos: self.pos, order: order, product: product});
                                                                new_line.set_quantity(line_record.quantity_y);
                                                                new_line.set_unit_price(0);
                                                                new_line.set_promotion({
                                                                    'prom_prod_id':line_record.product_y_id[0],
                                                                    'parent_product_id':line_record.product_x_id[0],
                                                                    'rule_name':promotion.promotion_code,
                                                                });
                                                                new_line.set_promotion_data(promotion);
                                                                new_line.set_is_rule_applied(true);
                                                                order.add_orderline(new_line);
                                                                line.set_child_line_id(new_line.id);
                                                                line.set_is_rule_applied(true);
                                                            }
                                                        }
                                                    }else if(line_record.operator == 'greater_than_or_eql'){
                                                        var data = order.get_product_qty(line.product.id);
    //													if(line.quantity >= line_record.quantity){
                                                        if(data.total_qty >= line_record.quantity){
                                                            if(line_record.product_y_id && line_record.product_y_id[0]){
                                                                var product = self.pos.db.get_product_by_id(line_record.product_y_id[0]);
                                                                var new_line = new models.Orderline({}, {pos: self.pos, order: order, product: product});
                                                                new_line.set_quantity(line_record.quantity_y);
                                                                new_line.set_unit_price(0);
                                                                new_line.set_promotion({
                                                                    'prom_prod_id':line_record.product_y_id[0],
                                                                    'parent_product_id':line_record.product_x_id[0],
                                                                    'rule_name':promotion.promotion_code,
                                                                });
                                                                new_line.set_promotion_data(promotion);
                                                                new_line.set_is_rule_applied(true);
                                                                order.add_orderline(new_line);
                                                                if(data.line_ids[0]){
                                                                    data.line_ids.map(function(line_id){
                                                                        var temp_line = order.get_orderline(line_id);
                                                                        if(temp_line){
                                                                            temp_line.set_child_line_id(new_line.id);
                                                                            temp_line.set_is_rule_applied(true);
                                                                        }
                                                                    });
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        });
                                    }
                                }else if(promotion && promotion.promotion_type == "buy_x_get_dis_y"){
                                    if(promotion.parent_product_ids && promotion.parent_product_ids[0] && (jQuery.inArray(line.product.id,promotion.parent_product_ids) != -1)){
                                        var disc_line_ids = [];
                                        _.each(promotion.pos_quntity_dis_ids, function(pos_quntity_dis_id){
                                            var disc_line_record = _.find(discount_list, function(obj) { return obj.id == pos_quntity_dis_id});
                                            if(disc_line_record){
                                                if(disc_line_record.product_id_dis && disc_line_record.product_id_dis[0]){
                                                    disc_line_ids.push(disc_line_record);
                                                }
                                            }
                                        });
                                        line.set_buy_x_get_dis_y({
                                            'disc_line_ids':disc_line_ids,
                                            'promotion':promotion,
                                        });
                                    }
                                    if(line.get_buy_x_get_dis_y().disc_line_ids){
                                        _.each(line.get_buy_x_get_dis_y().disc_line_ids, function(disc_line){
                                            _.each(lines, function(orderline){
                                                if(disc_line.product_id_dis && disc_line.product_id_dis[0] == orderline.product.id){
                                                    var count = 0;
                                                    _.each(order.get_orderlines(), function(_line){
                                                        if(_line.product.id == orderline.product.id){
                                                            count += 1;
                                                        }
                                                    });
                                                    if(count <= disc_line.qty){
                                                        var cart_line_qty = orderline.get_quantity();
                                                        if(cart_line_qty >= disc_line.qty){
                                                            var prmot_disc_lines = [];
                                                            var flag = true;
                                                            order.get_orderlines().map(function(o_line){
                                                                if(o_line.product.id == orderline.product.id){
                                                                    if(o_line.get_is_rule_applied()){
                                                                        flag = false;
                                                                    }
                                                                }
                                                            });
                                                            if(flag){
                                                                var extra_prod_qty = cart_line_qty - disc_line.qty;
                                                                if(extra_prod_qty != 0){
                                                                    orderline.set_quantity(disc_line.qty);
                                                                }
                                                                orderline.set_discount(disc_line.discount_dis_x);
                                                                orderline.set_buy_x_get_y_child_item({
                                                                    'rule_name':line.get_buy_x_get_dis_y().promotion.promotion_code,
                                                                    'promotion_type':line.get_buy_x_get_dis_y().promotion.promotion_type,
                                                                });
                                                                orderline.set_is_rule_applied(true);
                                                                self.pos.chrome.screens.products.order_widget.rerender_orderline(orderline);
                                                                if(extra_prod_qty != 0){
                                                                    var new_line = new models.Orderline({}, {pos: self.pos, order: order, product: orderline.product});
                                                                    new_line.set_quantity(extra_prod_qty);
                                                                    order.add_orderline(new_line);
                                                                }
                                                                return false;
                                                            }
                                                        }
                                                    }
                                                }
                                            });
                                        });
                                    }
                                }else if(promotion && promotion.promotion_type == "quantity_discount"){
                                    if(promotion.product_id_qty && promotion.product_id_qty[0] == line.product.id){
                                        var line_ids = [];
                                        _.each(promotion.pos_quntity_ids, function(pos_quntity_id){
                                            var line_record = _.find(pos_get_qty_discount_list, function(obj) { return obj.id == pos_quntity_id});
                                            if(line_record){
                                                if(line.get_quantity() >= line_record.quantity_dis){
                                                    if(line_record.discount_dis){
                                                        line.set_discount(line_record.discount_dis);
                                                        line.set_quantity_discount({
                                                            'rule_name':promotion.promotion_code,
                                                        });
                                                        line.set_promotion_data(promotion);
                                                        line.set_is_rule_applied(true);
                                                        self.pos.chrome.screens.products.order_widget.rerender_orderline(line);
                                                        return false;
                                                    }
                                                }
                                            }
                                        });
                                    }
                                }else if(promotion && promotion.promotion_type == "quantity_price"){
                                    if(promotion.product_id_amt && promotion.product_id_amt[0] == line.product.id){
                                        var line_ids = [];
                                        _.each(promotion.pos_quntity_amt_ids, function(pos_quntity_amt_id){
                                            var line_record = _.find(pos_qty_discount_amt, function(obj) { return obj.id == pos_quntity_amt_id});
                                            if(line_record){
                                                if(line.get_quantity() == line_record.quantity_amt){
                                                    if(line_record.discount_price){
                                                        line.set_discount_amt(line_record.discount_price);
                                                        line.set_discount_amt_rule(promotion.promotion_code);
                                                        line.set_promotion_data(promotion);
    //													line.set_unit_price(((line.get_unit_price()*line.get_quantity()) - line_record.discount_price)/line.get_quantity());
                                                        line.set_unit_price(line_record.discount_price);
                                                        line.set_is_rule_applied(true);
                                                        self.pos.chrome.screens.products.order_widget.rerender_orderline(line);
                                                        return false;
                                                    }
                                                }
                                            }
                                        });
                                    }
                                }else if(promotion && promotion.promotion_type == "discount_on_multi_product"){
                                    if(promotion.multi_products_discount_ids && promotion.multi_products_discount_ids[0]){
                                        _.each(promotion.multi_products_discount_ids, function(disc_line_id){
                                            var disc_line_record = _.find(pos_discount_multi_prods, function(obj) { return obj.id == disc_line_id});
                                            if(disc_line_record){
                                                self.check_products_for_disc(disc_line_record, promotion);
                                            }
                                        })
                                    }
                                }else if(promotion && promotion.promotion_type == "discount_on_multi_categ"){
                                    if(promotion.multi_categ_discount_ids && promotion.multi_categ_discount_ids[0]){
                                        _.each(promotion.multi_categ_discount_ids, function(disc_line_id){
                                            var disc_line_record = _.find(pos_discount_multi_categ, function(obj) { return obj.id == disc_line_id});
                                            if(disc_line_record){
                                                self.check_categ_for_disc(disc_line_record, promotion);
                                            }
                                        })
                                    }
                                }else if(promotion && promotion.promotion_type == "discount_on_above_price"){
                                    if(promotion && promotion.discount_price_ids && promotion.discount_price_ids[0]){
                                        _.each(promotion.discount_price_ids, function(line_id){
                                            var line_record = _.find(pos_discount_above_price, function(obj) { return obj.id == line_id});
                                            if(line_record.product_categ_ids.length > 0){
                                                if(line.product.pos_categ_id){
                                                    var product_category = self.pos.db.get_category_by_id(line.product.pos_categ_id[0])
                                                    if(product_category){
                                                        if($.inArray(product_category.id, line_record.product_categ_ids) != -1){
                                                            if(line_record.price && line_record.discount){
                                                                if(line.product.list_price >= line_record.price && line.quantity > 0){
                                                                    line.set_discount(line_record.discount);
                                                                    line.set_is_rule_applied(true);
                                                                    line.set_promotion_data(promotion);
                                                                    self.pos.chrome.screens.products.order_widget.rerender_orderline(line);
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        });
                                    }
                                }
                            }
                        });
                    }
                });
            }
        },
        check_products_for_disc: function(disc_line, promotion){
            var self = this;
            var product_ids = disc_line.product_ids;
            var discount = disc_line.products_discount;
            var order = self.pos.get_order();
            var lines = self.get_new_order_lines();
            var product_cmp_list = [];
            var orderline_ids = [];
            var products_qty = [];
            if(product_ids && product_ids[0] && discount){
                _.each(lines, function(line){
                    if(jQuery.inArray(line.product.id,product_ids) != -1){
                        product_cmp_list.push(line.product.id);
                        orderline_ids.push(line.id);
                        products_qty.push(line.get_quantity());
                    }
                });
                if(!_.contains(products_qty, 0)){
                    if(_.isEqual(_.sortBy(product_ids), _.sortBy(product_cmp_list))){
                        _.each(orderline_ids, function(orderline_id){
                            var orderline = order.get_orderline(orderline_id);
                            if(orderline && orderline.get_quantity() > 0){
                                orderline.set_discount(discount);
                                orderline.set_multi_prods_line_id(disc_line.id);
                                orderline.set_is_rule_applied(true);
                                orderline.set_combinational_product_rule(promotion.promotion_code);
                                self.pos.chrome.screens.products.order_widget.rerender_orderline(orderline);
                            }
                        });
                    }
                }
            }
        },
        check_categ_for_disc: function(disc_line, promotion){
            var self = this;
            var order = self.pos.get_order();
            var lines = self.get_new_order_lines();
            var categ_ids = disc_line.categ_ids;
            var discount = disc_line.categ_discount;
            if(categ_ids && categ_ids[0] && discount){
                _.each(categ_ids, function(categ_id){
                    var products = self.pos.db.get_product_by_category(categ_id);
                    if(products && products[0]){
                        _.each(lines, function(line){
                            if($.inArray(line.product, products) != -1){
                                line.set_discount(discount);
                                line.set_is_rule_applied(true);
                                line.set_multi_prod_categ_rule(promotion.promotion_code);
                                self.pos.chrome.screens.products.order_widget.rerender_orderline(line);
                            }
                        });
                    }
                });
            }
        },
        get_new_order_lines: function(){
            var self = this;
            var order = self.pos.get_order();
            var lines = order.get_orderlines();
            var new_lines = [];
            _.each(lines, function(line){
                if(line && line.get_quantity() > 0 && !line.get_is_rule_applied()){
                    new_lines.push(line);
                }
            });
            return new_lines;
        },
        calculate_discount_amt: function(){
            var self = this;
            var order = self.pos.get_order();
            var total = 0;
            if(order.get_orderlines().length){
                _.each(order.get_orderlines(),function(line){
                    if(!line.product.is_dummy_product){
                        total += line.get_display_price();
                    }
                });
            }
            var promotion_list = self.pos.pos_promotions;
            var discount = 0;
            var current_time = Number(moment(new Date().getTime()).locale('en').format("H"));
            if(promotion_list && promotion_list[0]){
                _.each(promotion_list, function(promotion){
                    if((Number(promotion.from_time) <= current_time && Number(promotion.to_time) > current_time) || (!promotion.from_time && !promotion.to_time)){
                        if(promotion.promotion_type == 'dicount_total'){
                            if(promotion.operator == 'greater_than_or_eql'){
                                if(promotion.total_amount && total >= promotion.total_amount){
                                    if(promotion.discount_product && promotion.discount_product[0]){
                                        discount = (total * promotion.total_discount)/100;
                                        order.set_discount_product_id(promotion.discount_product[0]);
                                    }
                                }
                            }else if(promotion.operator == 'is_eql_to'){
                                if(promotion.total_amount && total == promotion.total_amount){
                                    if(promotion.discount_product && promotion.discount_product[0]){
                                        discount = (total * promotion.total_discount)/100;
                                        order.set_discount_product_id(promotion.discount_product[0]);
                                    }
                                }
                            }
                        }
                    }
                });
            }
            return Number(discount);
        },
        get_total_without_tax: function() {
            var result = _super_Order.get_total_without_tax.call(this);
            if(this.pos.config.pos_promotion && this.get_order_total_discount()){
                return result - this.get_order_total_discount();
            } else{
                return result
            }
        },
        set_order_total_discount: function(order_total_discount){
            this.order_total_discount = order_total_discount;
        },
        get_order_total_discount: function(){
            return this.order_total_discount;
        },
        set_discount_price: function(discount_price){
            this.discount_price = discount_price;
        },
        get_discount_price: function(){
            return this.discount_price;
        },
        set_discount_product_id: function(discount_product_id){
            this.discount_product_id = discount_product_id;
        },
        get_discount_product_id: function(){
            return this.discount_product_id;
        },
        set_discount_history: function(disc){
            this.disc_history = disc;
        },
        get_discount_history: function(){
            return this.disc_history;
        },

     // Order History
        set_sequence:function(sequence){
            this.set('sequence',sequence);
        },
        get_sequence:function(){
            return this.get('sequence');
        },
        set_order_id: function(order_id){
            this.set('order_id', order_id);
        },
        get_order_id: function(){
            return this.get('order_id');
        },
        set_amount_paid: function(amount_paid) {
            this.set('amount_paid', amount_paid);
        },
        get_amount_paid: function() {
            return this.get('amount_paid');
        },
        set_amount_return: function(amount_return) {
            this.set('amount_return', amount_return);
        },
        get_amount_return: function() {
            return this.get('amount_return');
        },
        set_amount_tax: function(amount_tax) {
            this.set('amount_tax', amount_tax);
        },
        get_amount_tax: function() {
            return this.get('amount_tax');
        },
        set_amount_total: function(amount_total) {
            this.set('amount_total', amount_total);
        },
        get_amount_total: function() {
            return this.get('amount_total');
        },
        set_company_id: function(company_id) {
            this.set('company_id', company_id);
        },
        get_company_id: function() {
            return this.get('company_id');
        },
        set_date_order: function(date_order) {
            this.set('date_order', date_order);
        },
        get_date_order: function() {
            return this.get('date_order');
        },
        set_pos_reference: function(pos_reference) {
            this.set('pos_reference', pos_reference)
        },
        get_pos_reference: function() {
            return this.get('pos_reference')
        },
        set_user_name: function(user_id) {
            this.set('user_id', user_id);
        },
        get_user_name: function() {
            return this.get('user_id');
        },
        set_journal: function(statement_ids) {
            this.set('statement_ids', statement_ids)
        },
        get_journal: function() {
            return this.get('statement_ids');
        },
      //Rounding
        set_rounding_status: function(rounding_status) {
            this.rounding_status = rounding_status
        },
        get_rounding_status: function() {
            return this.rounding_status;
        },
        getNetTotalTaxIncluded: function() {
            var total = this.get_total_with_tax();
            return total
//         	if(this.get_rounding_status()){
// 	        	if(this.pos.config.enable_rounding && this.pos.config.rounding_options == 'digits'){
// //	        		var value = round_pr(Math.max(0,total))//decimalAdjust(total);
//                     var value = round_pr(total);
// 	                return value;
// 	        	}else if(this.pos.config.enable_rounding && this.pos.config.rounding_options == 'points'){
// 	        		var total = this.get_total_without_tax() + this.get_total_tax();
// 	                var value = decimalAdjust(total);
// 	                return value;
// 	        	}
//         	}else {
//         		return total
//         	}
        },
        get_rounding : function(){
            if(this.get_rounding_status()){
                var total = this ? this.get_total_with_tax() : 0;
                var rounding = this ? this.getNetTotalTaxIncluded() - total: 0;
                return rounding;
            }
        },
        get_due: function(paymentline) {
            if (!paymentline) {
                var due = this.getNetTotalTaxIncluded() - this.get_total_paid();
            } else {
                var due = this.getNetTotalTaxIncluded();
                var lines = this.paymentlines.models;
                for (var i = 0; i < lines.length; i++) {
                    if (lines[i] === paymentline) {
                        break;
                    } else {
                        due -= lines[i].get_amount();
                    }
                }
            }
            return round_pr(due,this.pos.currency.rounding);
        },
        get_change: function(paymentline) {
            if (!paymentline) {
                  if(this.get_total_paid() > 0 || this.get_cancel_order()){
//            		  var change = this.get_total_paid() - this.getNetTotalTaxIncluded() - this.get_order_total_discount();
                      if(this.get_order_total_discount()){
                          var change = this.get_total_paid() - this.getNetTotalTaxIncluded() - this.get_order_total_discount();
                      } else{
                          var change = this.get_total_paid() - this.getNetTotalTaxIncluded();
                      }
                  }else{
                      var change = this.get_amount_return();
                  }
            } else {
                var change = -this.getNetTotalTaxIncluded();
                var lines  = this.paymentlines.models;
                for (var i = 0; i < lines.length; i++) {
                    change += lines[i].get_amount();
                    if (lines[i] === paymentline) {
                        break;
                    }
                }
            }
            return round_pr(Math.max(0,change), this.pos.currency.rounding);
        },
        set_delivery_address: function(delivery_address){
            this.delivery_address = delivery_address;
        },
        get_delivery_address: function(){
            return this.delivery_address;
        },
        set_delivery_charge_amt: function(delivery_charge_amt){
            this.delivery_charge_amt = delivery_charge_amt;
        },
        get_delivery_charge_amt: function(){
            return this.delivery_charge_amt;
        },
        set_delivery_date: function(delivery_date) {
            this.delivery_date = delivery_date;
        },
        get_delivery_date: function() {
            return this.delivery_date;
        },
        set_delivery_time: function(delivery_time) {
            this.delivery_time = delivery_time;
        },
        get_delivery_time: function() {
            return this.delivery_time;
        },
        set_delivery: function(delivery) {
            this.delivery = delivery;
        },
        get_delivery: function() {
            return this.delivery;
        },
        set_delivery_charges: function(delivery_state) {
            this.delivery_state = delivery_state;
        },
        get_delivery_charges: function() {
            return this.delivery_state;
        },
        set_is_delivery: function(is_delivery) {
            this.is_delivery = is_delivery;
        },
        get_is_delivery: function() {
            return this.is_delivery;
        },
        count_to_be_deliver:function(){
            var self = this;
            var order = self.pos.get_order();
            var lines = order.get_orderlines();
            var count = 0;
            for(var i=0;i<lines.length;i++){
                if(lines[i].get_deliver_info()){
                    count = count + 1;
                }
            }
            if(count === 0){
                for(var j=0; j<lines.length;j++){
                    if(lines[j].get_delivery_charges_flag()){
                        order.remove_orderline(lines[j]);
                        order.set_is_delivery(false);
                        $('#delivery_mode').removeClass('deliver_on');
                    }
                }
            }
        },
        //loyalty
        set_loyalty_redeemed_point: function(val){
            this.set('loyalty_redeemed_point', Number(val).toFixed(2));
        },
        get_loyalty_redeemed_point: function(){
            return this.get('loyalty_redeemed_point') || Number(0.00);
        },
        set_loyalty_redeemed_amount: function(val){
            this.set('loyalty_redeemed_amount', val);
        },
        get_loyalty_redeemed_amount: function(){
            return this.get('loyalty_redeemed_amount') || 0.00;
        },
        set_loyalty_earned_point: function(val){
            this.set('loyalty_earned_point', val);
        },
        get_loyalty_earned_point: function(){
            return this.get('loyalty_earned_point') || 0.00;
        },
        set_loyalty_earned_amount: function(val){
            this.set('loyalty_earned_amount', val);
        },
        get_loyalty_earned_amount: function(){
            return this.get('loyalty_earned_amount') || 0.00;
        },
        get_loyalty_amount_by_point: function(point){
            if(this.pos.loyalty_config){
                return (point * this.pos.loyalty_config.to_amount) / this.pos.loyalty_config.points;
            }
        },
        set_giftcard: function(giftcard) {
            this.giftcard.push(giftcard)
        },
        get_giftcard: function() {
            return this.giftcard;
        },
        set_recharge_giftcard: function(recharge) {
            this.recharge.push(recharge)
        },
        get_recharge_giftcard: function(){
            return this.recharge;
        },
        set_redeem_giftcard: function(redeem) {
            this.redeem.push(redeem)
        },
        get_redeem_giftcard: function() {
            return this.redeem;
        },
        remove_card:function(code){ 
            var redeem = _.reject(this.redeem, function(objArr){ return objArr.redeem_card == code });
            this.redeem = redeem
        },
        set_free_data: function(freedata) {
            this.freedata = freedata;
        },
        get_free_data: function() {
            return this.freedata;
        },
        set_voucher: function(voucher) {
            this.voucher.push(voucher)
        },
        get_voucher: function() {
            return this.voucher;
        },
        remove_voucher: function(barcode, pid){
            this.voucher = _.reject(this.voucher, function(objArr){ return objArr.voucher_code == barcode && objArr.pid == pid; });
        },
        set_remaining_redeemption: function(vals){
            this.remaining_redeemption = vals;
        },
        get_remaining_redeemption: function(){
            return this.remaining_redeemption;
        },
        set_type_for_wallet: function(type_for_wallet) {
            this.set('type_for_wallet', type_for_wallet);
        },
        get_type_for_wallet: function() {
            return this.get('type_for_wallet');
        },
        set_change_amount_for_wallet: function(change_amount_for_wallet) {
            this.set('change_amount_for_wallet', change_amount_for_wallet);
        },
        get_change_amount_for_wallet: function() {
            return this.get('change_amount_for_wallet') ? Number(this.get('change_amount_for_wallet')) : 0.00;
        },
        set_use_wallet: function(use_wallet) {
            this.set('use_wallet', use_wallet);
        },
        get_use_wallet: function() {
            return this.get('use_wallet');
        },
        set_used_amount_from_wallet: function(used_amount_from_wallet) {
            this.set('used_amount_from_wallet', used_amount_from_wallet);
        },
        get_used_amount_from_wallet: function() {
            return this.get('used_amount_from_wallet');
        },
        get_dummy_product_ids: function(){
            var list_ids = [];
            if(this.pos.config.delivery_product_id)
                list_ids.push(this.pos.config.delivery_product_id[0]);
            if(this.pos.config.gift_card_product_id)
                list_ids.push(this.pos.config.gift_card_product_id[0]);
            if(this.pos.config.payment_product_id)
                list_ids.push(this.pos.config.payment_product_id[0]);
            if(this.pos.config.wallet_product)
                list_ids.push(this.pos.config.wallet_product[0]);
            if(this.pos.config.cancellation_charges_product_id)
                list_ids.push(this.pos.config.cancellation_charges_product_id[0]);
            if(this.pos.config.prod_for_payment)
                list_ids.push(this.pos.config.prod_for_payment[0]);
            if(this.pos.config.refund_amount_product_id)
                list_ids.push(this.pos.config.refund_amount_product_id[0]);
            if(this.pos.db.get_dummy_product_ids().length > 0){
                this.pos.db.get_dummy_product_ids().map(function(dummy_id){
                    if(!_.contains(list_ids, dummy_id)){
                        list_ids.push(dummy_id);
                    }
                });
            }
            return list_ids;
        },
        remove_orderline: function(line){
            var self = this;
            _super_Order.remove_orderline.call(this, line);
            if(line){
                var lines = this.get_orderlines();
                if(line && line.get_child_line_id()){
                    var child_line = self.get_orderline(line.get_child_line_id());
                    lines.map(function(_line){
                        if(_line.get_child_line_id() == line.get_child_line_id()){
                            _line.set_child_line_id(false);
                            _line.set_is_rule_applied(false);
                        }
                    });
                    if(child_line){
                        line.set_child_line_id(false);
                        line.set_is_rule_applied(false);
                        self.remove_orderline(child_line);
                        self.apply_promotion();
                    }
                }else if(line.get_buy_x_get_dis_y()){
                    _.each(lines, function(_line){
                        if(_line && _line.get_buy_x_get_y_child_item()){
                            _line.set_discount(0);
                            _line.set_buy_x_get_y_child_item({});
                            _line.set_is_rule_applied(false);
                            self.pos.chrome.screens.products.order_widget.rerender_orderline(_line);
                        }
                    });
                }else if(line.get_multi_prods_line_id()){
                    var multi_prod_id = line.get_multi_prods_line_id() || false;
                    if(multi_prod_id){
                        _.each(lines, function(_line){
                            if(_line && _line.get_multi_prods_line_id() == multi_prod_id){
                                _line.set_discount(0);
                                _line.set_is_rule_applied(false);
                                _line.set_combinational_product_rule(false);
                                self.pos.chrome.screens.products.order_widget.rerender_orderline(_line);
                            }
                        });
                    }
                }
            }
        },
        add_paymentline: function(cashregister) {
            _super_Order.add_paymentline.call(this,cashregister);
//From credit Debit module bad inheritance due to unfamilier with code.
//        	this.assert_editable();
//            var newPaymentline = new models.Paymentline({},{order: this, cashregister:cashregister, pos: this.pos});
//            if(cashregister.journal.type == 'bank'){
//                if(this.pos.get_order().get_total_with_tax() >= 0){
//                    newPaymentline.set_amount( Math.max(this.pos.get_order().get_total_with_tax(),0) );
//                }else {
//                    newPaymentline.set_amount( Math.min(this.pos.get_order().get_total_with_tax(),0) );
//                }
//            }
//            this.paymentlines.add(newPaymentline);
//            this.select_paymentline(newPaymentline);
// Credit debit finish here.
            var total = this.get_total_with_tax();
            var paymentline = this.get_paymentlines();
            _.each(paymentline, function(line){
                if(line.selected && total < 0){
                    line.set_amount(total);
                }
            });
        },
        add_paymentline_by_journal: function(cashregister) {
            this.assert_editable();
            var newPaymentline = new models.Paymentline({}, {order: this, cashregister:cashregister, pos: this.pos})
            var newPaymentline = new models.Paymentline({}, {order: this, cashregister:cashregister, pos: this.pos})
            if((this.pos.get_order().get_due() > 0) && (this.pos.get_order().get_client().remaining_credit_amount > this.pos.get_order().get_due())) {
                newPaymentline.set_amount(Math.min(this.pos.get_order().get_due(),this.pos.get_order().get_client().remaining_credit_amount));
            }else if((this.pos.get_order().get_due() > 0) && (this.pos.get_order().get_client().remaining_credit_amount < this.pos.get_order().get_due())) {
                newPaymentline.set_amount(Math.min(this.pos.get_order().get_due(),this.pos.get_order().get_client().remaining_credit_amount));
            }else if(this.pos.get_order().get_due() > 0) {
                    newPaymentline.set_amount( Math.max(this.pos.get_order().get_due(),0) );
            }
            this.paymentlines.add(newPaymentline);
            this.select_paymentline(newPaymentline);
        },
        get_remaining_credit: function(){
            var credit_total = 0.00,use_credit = 0.00;
            var self = this;
            var partner = self.pos.get_client();
            if(partner && partner.deposite_info){
                var client_account = partner.deposite_info['content'];
                var credit_detail = this.get_credit_detail();
                _.each(client_account, function(values){
                    credit_total = values.amount + credit_total
                });
                if(credit_detail && credit_detail.length > 0 && client_account && client_account.length > 0){
                    for (var i=0;i<client_account.length;i++){
                        for(var j=0;j<credit_detail.length;j++){
                            if(client_account[i].id == credit_detail[j].journal_id){
                                use_credit += Math.abs(credit_detail[j].amount)
                            }
                        }
                    }
                }
            }
            if(use_credit){
                return 	credit_total - use_credit;
            } else{
                return false
            }
        },

        export_as_JSON: function() {
            var self = this;
            var orders = _super_Order.export_as_JSON.call(this);
            var parent_return_order = '';
            var ret_o_id = this.get_ret_o_id();
            var ret_o_ref = this.get_ret_o_ref();
            var return_seq = 0;
            if (ret_o_id) {
                parent_return_order = this.get_ret_o_id();
            }
            var backOrders_list = [];
            _.each(this.get_orderlines(),function(item) {
                if (item.get_back_order()) {
                    backOrders_list.push(item.get_back_order());
                }
            });
            var unique_backOrders = "";
            for ( var i = 0 ; i < backOrders_list.length ; ++i ) {
                if ( unique_backOrders.indexOf(backOrders_list[i]) == -1 && backOrders_list[i] != "" )
                    unique_backOrders += backOrders_list[i] + ', ';
            }
            var cancel_orders = '';
            _.each(self.get_orderlines(), function(line){
                if(line.get_cancel_item()){
                    cancel_orders += " "+line.get_cancel_item();
                }
            });
            if(!this.get_merge_table_ids()){
                if(this.table && this.table.id){
                    if(!this.get_merge_table_ids()){
                        this.set_merge_table_ids([this.table.id]);
                    }else{
                        if(!_.contains(this.get_merge_table_ids(),this.table.id)){
                            this.set_merge_table_ids([this.table.id]);
                        }
                    }
                }
            }
            var new_val = {
                is_kitchen_order: this.is_kitchen_order,
                signature: this.get_signature(),
                customer_email: this.get_ereceipt_mail(),
                prefer_ereceipt: this.get_prefer_ereceipt(),
                order_note: this.get_order_note(),
                parent_return_order: parent_return_order,
                return_seq: return_seq || 0,
                back_order: unique_backOrders,
                sale_mode: this.get_sale_mode(),
                old_order_id: this.get_order_id(),
                sequence: this.get_sequence(),
                pos_reference: this.get_pos_reference(),
                rounding: this.get_rounding(),
                // is_rounding: this.pos.config.enable_rounding,
                // rounding_option: this.pos.config.enable_rounding ? this.pos.config.rounding_options : false,
                delivery_date: this.get_delivery_date(),
                delivery_time: this.get_delivery_time(),
                delivery_address: this.get_delivery_address(),
                delivery_charge_amt: this.get_delivery_charge_amt(),
                loyalty_redeemed_point: this.get_loyalty_redeemed_point() || false,
                loyalty_redeemed_amount: this.get_loyalty_redeemed_amount() || false,
                loyalty_earned_point: this.get_loyalty_earned_point() || false,
                loyalty_earned_amount: this.get_loyalty_earned_amount() || false,
                giftcard: this.get_giftcard() || false,
                redeem: this.get_redeem_giftcard() || false,
                recharge: this.get_recharge_giftcard() || false,
                voucher: this.get_voucher() || false,
                wallet_type: this.get_type_for_wallet() || false,
                change_amount_for_wallet: this.get_change_amount_for_wallet() || 0.00,
                used_amount_from_wallet: this.get_used_amount_from_wallet() || false,
                amount_paid: this.get_total_paid() - (this.get_change() - Number(this.get_change_amount_for_wallet())),
                amount_return: this.get_change() - Number(this.get_change_amount_for_wallet()),
                //Reservation
                amount_due: this.get_due() ? (this.get_due() + Number(this.get_change_amount_for_wallet())): 0.00,
                reserved: this.get_reservation_mode() || false,
                reserve_delivery_date: this.get_reserve_delivery_date() || false,
                cancel_order_ref: cancel_orders || false,
                cancel_order: this.get_cancel_order() || false,
                set_as_draft: this.get_draft_order() || false,
                // customer_email: this.get_client() ? this.get_client().email : false,
                fresh_order: this.get_fresh_order() || false,
                partial_pay: this.get_partial_pay() || false,
                store_id : self.pos.get_cashier().default_store_id ? self.pos.get_cashier().default_store_id[0] : false,
                rating: this.get_rating() || '0',
                salesman_id: this.get_salesman_id() || this.pos.get_cashier().id,
                credit_type: this.get_type_for_credit() || false,
                order_make_picking: this.get_order_make_picking() || false,
                credit_detail: this.get_credit_detail(),
                is_debit : this.get_is_debit() || false,
                delivery_type: this.get_delivery_type(),
                delivery_user_id: (this.get_delivery_user_id() != 0 ? this.get_delivery_user_id() : false),
                to_be_deliver: this.get_deliver_mode() || false,
                order_on_debit: this.get_order_on_debit() || false,
                pos_normal_receipt_html: this.get_pos_normal_receipt_html() || '',
                pos_xml_receipt_html: this.get_pos_xml_receipt_html() || '',
                increment_number: this.pos.zero_pad(this.pos.increment_number || 0, self.pos.last_token_number.toString().length),
                is_update_increnement_number: this.get_is_update_increnement_number() || false,
                temp_increment_number: this.get_temp_increment_number() || false,
                table_ids : this.get_merge_table_ids() || [],
            }
            $.extend(orders, new_val);
            return orders;
        },
        export_for_printing: function(){
            var orders = _super_Order.export_for_printing.call(this);
            var order_no = this.get_name() || false ;
            var self = this;
            var order_no = order_no ? this.get_name().replace(_t('Order '),'') : false;
            var last_paid_amt = 0;
            var currentOrderLines = this.get_orderlines();
            if(currentOrderLines.length > 0) {
                _.each(currentOrderLines,function(item) {
                    if(item.get_product().id == self.pos.config.prod_for_credit_payment[0] ){
                        last_paid_amt = item.get_display_price()
                    }
                });
            }
            var total_paid_amt = this.get_total_paid()-last_paid_amt
            var new_val = {
                order_note: this.get_order_note() || false,
                ret_o_id: this.get_ret_o_id(),
                order_no: order_no,
                reprint_payment: this.get_journal() || false,
                ref: this.get_pos_reference() || false,
                date_order: this.get_date_order() || false,
                rounding: this.get_rounding(),
                net_amount: this.getNetTotalTaxIncluded(),
                total_points: this.get_total_loyalty_points() || false,
                earned_points: this.get_loyalty_earned_point() || false,
                redeem_points: this.get_loyalty_redeemed_point() || false,
                client_points: this.get_client() && this.get_client().total_remaining_points ? this.get_client().total_remaining_points.toFixed(2) : false,
                giftcard: this.get_giftcard() || false,
                recharge: this.get_recharge_giftcard() || false,
                redeem:this.get_redeem_giftcard() || false,
                free:this.get_free_data()|| false,
                remaining_redeemption: this.get_remaining_redeemption() || false,
             // Sale Order
                sale_order_name: this.get_sale_order_name() || false,
                invoice_name: this.get_invoice_name() || false,
                sale_note: this.get_sale_note() || '',
                signature: this.get_signature() || '',
                // Wallet
                change_amount_for_wallet: this.get_change_amount_for_wallet() || false,
                used_amount_from_wallet: this.get_used_amount_from_wallet() || false,
                amount_paid: this.get_total_paid() - (this.get_change() - Number(this.get_change_amount_for_wallet())),
                amount_return: this.get_change() - Number(this.get_change_amount_for_wallet()),
                //Reservation
                amount_due: this.get_due() ? (this.get_due() + Number(this.get_change_amount_for_wallet())): 0.00,
                reprint_payment: this.get_journal() || false,
                ref: this.get_pos_reference() || false,
                last_paid_amt: last_paid_amt || 0,
                total_paid_amt: total_paid_amt || false,
                amount_due: this.get_due() ? this.get_due() : 0.00,
                old_order_id: this.get_order_id(),
                reserve_delivery_date: moment(this.get_reserve_delivery_date()).locale('en').format('L') || false,
                delivery_date: this.get_delivery_date() || false,
                delivery_time: this.get_delivery_time() || false,
                delivery_address: this.get_delivery_address() || false,
                delivery_type: this.get_delivery_type() || false,
                delivery_user_id: this.get_delivery_user_id() || false,
                increment_number: this.pos.zero_pad(this.pos.increment_number || 0, self.pos.last_token_number.toString().length),
                is_update_increnement_number: this.get_is_update_increnement_number() || false,
                temp_increment_number: this.get_temp_increment_number() || false,
            };
            $.extend(orders, new_val);
            return orders;
        },
        set_pos_xml_receipt_html: function(pos_xml_receipt_html){
            this.pos_xml_receipt_html = pos_xml_receipt_html;
        },
        get_pos_xml_receipt_html: function(){
            return this.pos_xml_receipt_html;
        },
        set_pos_normal_receipt_html: function(pos_normal_receipt_html){
            this.pos_normal_receipt_html = pos_normal_receipt_html;
        },
        get_pos_normal_receipt_html: function(){
            return this.pos_normal_receipt_html;
        },
        set_order_on_debit: function(order_on_debit){
            this.order_on_debit = order_on_debit;
        },
        get_order_on_debit: function(){
            return this.order_on_debit;
        },
        set_deliver_mode: function(mode){
            this.set('delivery_mode',mode)
        },
        get_deliver_mode: function(){
            return this.get('delivery_mode')
        },
        set_custom_uom_id: function(uom_id){
            this.set('custom_uom_id',uom_id);
        },
        get_custom_uom_id: function(){
            return this.get('custom_uom_id');
        },
        apply_uom: function(){
            var self = this;
            var order = self.pos.get_order();
            var uom_id = order.get_custom_uom_id();
            if(uom_id){
                var orderline = order.get_selected_orderline();
                var selected_uom = self.pos.units_by_id[uom_id];

                orderline.uom_id = [];
                orderline.uom_id[0] = uom_id;
                orderline.uom_id[1] = selected_uom.display_name;
                order.remove_orderline(orderline);
                order.add_orderline(orderline);
                var latest_price = order.get_latest_price(selected_uom, orderline.product);
                order.get_selected_orderline().set_unit_price(latest_price);
                return true
            } else{
                return false
            }
        },
        get_units_by_category: function(uom_list, categ_id){
            var uom_by_categ = []
            for (var uom in uom_list){
                if(uom_list[uom].category_id[0] == categ_id[0]){
                    uom_by_categ.push(uom_list[uom]);
                }
            }
            return uom_by_categ;
        },
        find_reference_unit_price: function(product, product_uom){
            return product.lst_price;
        },
        get_latest_price: function(uom, product){
            var uom_by_category = this.get_units_by_category(this.pos.units_by_id, uom.category_id);
            var product_uom = this.pos.units_by_id[product.uom_id[0]];
            var ref_price = this.find_reference_unit_price(product, product_uom);
            var ref_unit = null;
            for (var i in uom_by_category){
                if(uom_by_category[i].uom_type == 'reference'){
                    ref_unit = uom_by_category[i];
                    break;
                }
            }
            if(ref_unit){

                if(uom.uom_type == 'bigger'){
                    return (ref_price * uom.factor_inv);

                }
                else if(uom.uom_type == 'smaller'){
                    return (ref_price / uom.factor);
                }
                else if(uom.uom_type == 'reference'){
                    return ref_price;
                }
            }
            return product.price;
        },
        remove_paymentline: function(line){
            this.set_loyalty_redeemed_point(Number(this.get_loyalty_redeemed_point() - line.get_loyalty_point()));
            this.set_loyalty_redeemed_amount(Number(this.get_loyalty_amount_by_point(this.get_loyalty_redeemed_point())));
            _super_Order.remove_paymentline.apply(this, arguments);
        },
        set_delivery_type: function(delivery_type){
            this.delivery_type = delivery_type;
        },
        get_delivery_type: function(){
            return this.delivery_type;
        },
        set_delivery_payment_data: function(delivery_payment_data){
            this.delivery_payment_data = delivery_payment_data;
        },
        get_delivery_payment_data: function(){
            return this.delivery_payment_data;
        },
        set_delivery_user_id: function(delivery_user_id){
            this.delivery_user_id = delivery_user_id;
        },
        get_delivery_user_id: function(){
            return this.delivery_user_id;
        },
//        count_to_be_deliver:function(){
//	    	var self = this;
//	    	var order = self.pos.get_order();
//	    	var lines = order.get_orderlines();
//	    	var count = 0;
//			for(var i=0;i<lines.length;i++){
//				if(lines[i].get_deliver_info()){
//					count = count + 1;
//				}
//			}
//			if(count === 0){
//				for(var j=0; j<lines.length;j++){
//					if(lines[j].get_delivery_charges_flag()){
//						order.remove_orderline(lines[j]);
//						order.set_is_delivery(false);
//						$('#delivery_mode').removeClass('deliver_on');
//					}
//				}
//			}
//	    },
        get_total_loyalty_points: function(){
            var temp = 0.00
            if(this.get_client()){
                temp = Number(this.get_client().total_remaining_points)
                        + Number(this.get_loyalty_earned_point())
                        - Number(this.get_loyalty_redeemed_point())
            }
            return temp.toFixed(2)
        },
        set_type_for_credit: function(type_for_credit) {
            this.set('type_for_credit', type_for_credit);
        },
        get_type_for_credit: function() {
            return this.get('type_for_credit');
        },
        set_ledger_click: function(ledger_click){
            this.ledger_click = ledger_click;
        },
        get_ledger_click: function() {
            return this.ledger_click;
        },
        set_use_credit: function(use_credit) {
            this.set('use_credit', use_credit);
        },
        get_use_credit: function() {
            return this.get('use_credit');
        },
        set_paying_order: function(val){
            this.set('paying_order',val)
        },
        get_paying_order: function(){
            return this.get('paying_order')
        },
        set_salesman_id: function(salesman_id){
            this.set('salesman_id',salesman_id);
        },
        get_salesman_id: function(){
            return this.get('salesman_id');
        },
        set_result: function(result) {
            this.set('result', result);
        },
        get_result: function() {
            return this.get('result');
        },
        // POS Serial/lots
        set_print_serial: function(val) {
            this.print_serial = val
        },
        get_print_serial: function() {
            return this.print_serial;
        },
        display_lot_popup: function() {
            var self = this;
            var order_line = this.get_selected_orderline();
            if(order_line && order_line.product.type == "product"){
                var pack_lot_lines =  order_line.compute_lot_lines();
                var product_id = order_line.get_product().id;
                if(this.pos.config.enable_pos_serial){
                    if(product_id){
                        var params = {
                            model: 'stock.production.lot',
                            method: 'search_serial_lot_data',
                            args: [product_id],
                        }
                        rpc.query(params, {async: false}).then(function(serials){
                            if(serials){
                                self.pos.gui.show_popup('packlotline', {
                                    'title': _t('Lot/Serial Number(s) Required'),
                                    'pack_lot_lines': pack_lot_lines,
                                    'order': self,
                                    'serials': serials
                                });
                            }
                        });
                    }
                } else {
                    self.pos.gui.show_popup('packlotline', {
                        'title': _t('Lot/Serial Number(s) Required'),
                        'pack_lot_lines': pack_lot_lines,
                        'order': self,
                        'serials': []
                    });
                }
            }
        },
//        Product summary report
        set_order_summary_report_mode: function(order_summary_report_mode) {
            this.order_summary_report_mode = order_summary_report_mode;
        },
        get_order_summary_report_mode: function() {
            return this.order_summary_report_mode;
        },
        set_product_summary_report :function(product_summary_report) {
            this.product_summary_report = product_summary_report;
        },
        get_product_summary_report: function() {
            return this.product_summary_report;
        },
    });

    var _super_orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        initialize: function(attr,options){
            _super_orderline.initialize.call(this, attr, options);
            this.state = 'waiting';
            this.line_note = '';
            this.oid = null;
            this.backorder = null;
            this.bag_color = false;
            this.is_bag = false;
            this.promotion = {};
            this.child_line_id = false;
            this.product_ids = false;
            this.buy_x_get_y_child_item = false;
            this.discount_line_id = false;
            this.discount_rule_name = false;
            this.quantity_discount = false;
            this.discount_amt_rule = false;
            this.discount_amt = false;
            this.multi_prods_line_id = false;
            this.is_rule_applied = false;
            this.combinational_product_rule = false;
            this.multi_prod_categ_rule = false;
            this.disc_above_price = false;
            this.set({
                location_id: false,
                location_name: false,
            });
            this.cancel_item = false;
            this.consider_qty = 0;
            this.return_valid_days = 0;
            this.uom_id = this.product ? this.product.uom_id: [];

            this.is_bomline = false;
            this.bom_line = [];
            this.bom_line_start = [];
            this.line_ref = false;
            this.combo_prod_info = false;
        },
        set_combo_prod_info: function(combo_prod_info){
            this.combo_prod_info = combo_prod_info;
            this.trigger('change',this);
        },
        get_combo_prod_info: function(){
            return this.combo_prod_info;
        },
        set_kitchen_item_priority: function(kitchen_item_priority){
            this.kitchen_item_priority = kitchen_item_priority;
            this.trigger('change',this);
        },
        get_kitchen_item_priority: function(){
            return this.kitchen_item_priority;
        },
        get_orderline_ref: function(){
            return this.line_ref;
        },
        set_orderline_ref : function(line_ref){
            this.line_ref = line_ref;
            this.trigger('change',this);
        },
        get_bom_line_at_start: function(){
            return this.bom_line_start;
        },
        set_bom_line_at_start : function(bom_data){
            var self = this;
            if(this.bom_line && this.bom_line.length > 0){
                this.bom_line = _.uniq(_.union(this.bom_line, bom_data, false, function(item, key, id){ return item.id; }));
            }else{
                this.bom_line_start.push(bom_data)
            }
        },
        get_each_bom_line : function(){
            var self = this;
            var get_rpc_bom = [];
            return new Promise(function(resolve, reject){
                var params = {
                    model: 'mrp.bom.line',
                    method: 'search_read',
                    domain : [['id', 'in', self.pos.db.bom_line_ids]],
                    fields: ['id','parent_product_tmpl_id','product_id','bom_id','product_qty'],
                }
                rpc.query(params, {async: false}).then(function(result) {
                    if(result){
                        result['select'] = true;
                        self.pos.set({'get_rpc_bom':result})
                        resolve();
                    }else{
                        reject();
                    }
                });
            });            
        },
        set_bom_line: function(bom_data){
            var self = this;
            if(this.bom_line && this.bom_line.length > 0){
                this.bom_line = _.uniq(_.union(this.bom_line, bom_data, false, function(item, key, id){ return item.id; }));
            }else{
                this.bom_line.push(bom_data)
            }
        },
        get_bom_line: function(){
            return this.bom_line;
        },
        return_bom_line_data :function(){
            var self = this;
            var custom_bom_line = this.bom_line;
            var default_bom_line = this.bom_line_start;
            var returned_bom_line = [];
            if(default_bom_line.length > 0 || custom_bom_line.length > 0){
                if(custom_bom_line.length > 0 ){
                    _.each(custom_bom_line[0],function(bom_line){
                        var MAX_LENGTH = 24; // 40 * line ratio of .6
                        var wrapped = [];
                        var name = self.pos.db.get_product_by_id(bom_line.product_id[0]).display_name;
                        var current_line = "";
                        while (name.length > 0) {
                            var space_index = name.indexOf(" ");
                            if (space_index === -1) {
                                space_index = name.length;
                            }
                            if (current_line.length + space_index > MAX_LENGTH) {
                                if (current_line.length) {
                                    wrapped.push(current_line);
                                }
                                current_line = "";
                            }
                            current_line += name.slice(0, space_index + 1);
                            name = name.slice(space_index + 1);
                        }
                        if (current_line.length) {
                            wrapped.push(current_line);
                        }
                        returned_bom_line.push({
                            'bom_product_name_wrapped':wrapped,
                            'bom_line_product_id' : bom_line.product_id[0],
                            'bom_id':bom_line.bom_id[0],
                            'bom_line_id':bom_line.id,
                            'bom_selected':bom_line.select,
                            'bom_line_qty':bom_line.product_qty,
                        })
                    });
                }else{
                    _.each(default_bom_line[0],function(bom_line){
                        var MAX_LENGTH = 24; // 40 * line ratio of .6
                        var wrapped = [];
                        var name = self.pos.db.get_product_by_id(bom_line.product_id[0]).display_name;
                        var current_line = "";
                        while (name.length > 0) {
                            var space_index = name.indexOf(" ");
                            if (space_index === -1) {
                                space_index = name.length;
                            }
                            if (current_line.length + space_index > MAX_LENGTH) {
                                if (current_line.length) {
                                    wrapped.push(current_line);
                                }
                                current_line = "";
                            }
                            current_line += name.slice(0, space_index + 1);
                            name = name.slice(space_index + 1);
                        }
                        if (current_line.length) {
                            wrapped.push(current_line);
                        }
                        returned_bom_line.push({
                            'bom_product_name_wrapped':wrapped,
                            'bom_line_product_id' : bom_line.product_id[0],
                            'bom_id':bom_line.bom_id[0],
                            'bom_line_id':bom_line.id,
                            'bom_selected':bom_line.select,
                            'bom_line_qty':bom_line.product_qty,
                        })
                    });
                }
            }
            else{
                returned_bom_line = [];
            }
            return returned_bom_line;
        },
        // get_each_bom_line : function(){
        //     var get_rpc_bom = [];
        //     console.log("this.pos.db.bom_line_ids---->",this.pos.db.bom_line_ids)
        //     var params = {
        //         model: 'mrp.bom.line',
        //         method: 'search_read',
        //         fields: ['product_id','parent_product_tmpl_id'],
        //         domain : [['id', 'in', this.pos.db.bom_line_ids]],
        //     }
        //     rpc.query(params, {async: false}).then(function(result){
        //         if(result){
        //             result['select'] = true;
        //             get_rpc_bom.push(result);
        //         }
        //         return get_rpc_bom;
        //     }).catch(function(){
        //         self.pos.db.notification('danger',"Connection lost");
        //     });
        // },
        set_from_credit: function(from_credit) {
            this.from_credit = from_credit;
        },
        get_from_credit: function() {
            return this.from_credit;
        },
        set_return_valid_days: function(return_valid_days){
            this.return_valid_days = return_valid_days;
        },
        get_return_valid_days: function(return_valid_days){
            return this.return_valid_days;
        },
        set_input_lot_serial: function(serial_name) {
//       	 Remove All Lots
            var pack_lot_lines = this.pack_lot_lines;
            var len = pack_lot_lines.length;
            var cids = [];
            for(var i=0; i<len; i++){
                var lot_line = pack_lot_lines.models[i];
                cids.push(lot_line.cid);
            }
            for(var j in cids){
                var lot_model = pack_lot_lines.get({cid: cids[j]});
                lot_model.remove();
            }
            // Add new lots
            for(var k=0; k<serial_name.length; k++){
                var lot_model = new models.Packlotline({}, {'order_line': this});
                lot_model.set_lot_name(serial_name[k].lot_name);
                if(pack_lot_lines){
                    pack_lot_lines.add(lot_model);
                }
            }
            this.trigger('change',this);
       },
        set_cancel_item: function(val){
            this.set('cancel_item', val)
        },
        get_cancel_item: function(){
            return this.get('cancel_item');
        },
        set_consider_qty: function(val){
            this.set('consider_qty', val)
        },
        get_consider_qty: function(){
            return this.get('consider_qty');
        },
        set_location_id: function(location_id){
            this.set({
                'location_id': location_id,
            });
        },
        set_cancel_process: function(oid) {
            this.set('cancel_process', oid)
        },
        get_cancel_process: function() {
            return this.get('cancel_process');
        },
        set_cancel_item_id: function(val) {
            this.set('cancel_item_id', val)
        },
        get_cancel_item_id: function() {
            return this.get('cancel_item_id');
        },
        set_line_status: function(val) {
            this.set('line_status', val)
        },
        get_line_status: function() {
            return this.get('line_status');
        },
        get_location_id: function(){
            return this.get('location_id');
        },
        set_location_name: function(location_name){
            this.set({
                'location_name': location_name,
            });
        },
        get_location_name: function(){
            return this.get('location_name');
        },
        set_quantity: function(quantity, keep_price){
            if(quantity === 'remove'){
                this.set_oid('');
                this.pos.get_order().remove_orderline(this);
                return;
            }else{
                _super_orderline.set_quantity.call(this, quantity, keep_price);
            }
            this.trigger('change',this);
        },
        set_bag_color: function(bag_color) {
            this.bag_color = bag_color;
        },
        get_bag_color: function() {
            return this.get('bag_color');
        },
        set_is_bag: function(is_bag){
            this.is_bag = is_bag;
        },
        get_is_bag: function(){
            return this.is_bag;
        },
        set_line_note: function(line_note) {
            this.set('line_note', line_note);
        },
        get_line_note: function() {
            return this.get('line_note');
        },
        set_oid: function(oid) {
            this.set('oid', oid)
        },
        get_oid: function() {
            return this.get('oid');
        },
        set_back_order: function(backorder) {
            this.set('backorder', backorder);
        },
        get_back_order: function() {
            return this.get('backorder');
        },
        set_delivery_charges_color: function(delivery_charges_color) {
            this.delivery_charges_color = delivery_charges_color;
        },
        get_delivery_charges_color: function() {
            return this.get('delivery_charges_color');
        },
        set_deliver_info: function(deliver_info) {
            this.set('deliver_info', deliver_info);
        },
        get_deliver_info: function() {
            return this.get('deliver_info');
        },
        set_delivery_charges_flag: function(delivery_charge_flag) {
            this.set('delivery_charge_flag',delivery_charge_flag);
        },
        get_delivery_charges_flag: function() {
            return this.get('delivery_charge_flag');
        },
        set_original_price: function(price){
            this.set('original_price', price)
        },
        get_original_price: function(){
            return this.get('original_price')
        },
        set_promotion_data: function(data){
            this.promotion_data = data;
        },
        get_promotion_data: function(){
            return this.promotion_data
        },
        set_state: function(state) {
            this.state = state;
            this.trigger('change',this);
        },
        get_state: function(){
            return this.state;
        },
        init_from_JSON: function(json) {
            _super_orderline.init_from_JSON.apply(this, arguments)
            this.set_original_price(json.original_price);
            this.kitchen_item_priority = json.priority;
        },
        export_as_JSON: function() {
            var lines = _super_orderline.export_as_JSON.call(this);
            var oid = this.get_oid();
            var return_process = oid;
            var return_qty = this.get_quantity();
            var order_ref = this.pos.get_order() ? this.pos.get_order().get_ret_o_id() : false;
            var default_stock_location = this.pos.config.stock_location_id ? this.pos.config.stock_location_id[0] : false;
            var serials = "Serial No(s).: ";
            var back_ser = "";
            var serials_lot = [];
//            var return_valid_days = 0;
//            if(!this.product.non_refundable){
//            	if(this.product.return_valid_days > 0){
//                	return_valid_days = this.product.return_valid_days;
//                }else{
//                	if(this.product.pos_categ_id && this.product.pos_categ_id[0]){
//                		var categ = self.pos.db.category_by_id[this.product.pos_categ_id[0]];
//                		while (categ.parent_id && categ.parent_id[0]) {
//                			categ = self.pos.db.category_by_id[categ.parent_id[0]];
//                			if(categ && categ.return_valid_days > 0){
//                				return_valid_days = categ.return_valid_days;
//                			}
//                		}
//                	}
//                }
//            }else{
//            	return_valid_days = 0;
//            }
            if(this.pack_lot_lines && this.pack_lot_lines.models){
                var self = this;
                _.each(this.pack_lot_lines.models,function(lot) {
                    if(lot && lot.get('lot_name')){
                        if($.inArray(lot.get('lot_name'), serials_lot) == -1){
                            var count = 0;
                            serials_lot.push(lot.get('lot_name'));
                            _.each(self.pack_lot_lines.models,function(lot1) {
                                if(lot1 && lot1.get('lot_name')){
                                    if(lot1.get('lot_name') == lot.get('lot_name')){
                                        count ++;
                                    }
                                }
                            });
                            serials += lot.get('lot_name')+"("+count+")"+", ";
                        }
                    }
                });
            } else {
                serials = "";
            }
            this.lots = serials;
            var combo_ext_line_info = [];
            if(this.product.is_combo && this.combo_prod_info.length > 0){
                _.each(this.combo_prod_info, function(item){
                    combo_ext_line_info.push([0, 0, {'product_id':item.product.id, 'qty':item.qty, 'price':item.price}]);
                });
            }
            // lines.combo_ext_line_info = (this.product.is_combo ? combo_ext_line_info : [])
            // console.log("----3731---->",this.product.is_combo ? combo_ext_line_info : [])
            var new_attr = {
                line_note: this.get_line_note(),
                cost_price: this.product.standard_price,
                return_process: return_process,
                return_qty: parseInt(return_qty),
                back_order: this.get_back_order(),
                deliver: this.get_deliver_info(),
                location_id: this.get_location_id() || default_stock_location,
                //reservation
                cancel_item: this.get_cancel_item() || false,
                cancel_process: this.get_cancel_process() || false,
                cancel_qty: this.get_quantity() || false,
                consider_qty : this.get_consider_qty(),
                cancel_item_id: this.get_cancel_item_id() || false,
                new_line_status: this.get_line_status() || false,
                serial_nums: this.lots || false,
                return_valid_days: this.get_return_valid_days(),
                from_credit:this.get_from_credit(),
                uom_id: this.uom_id,
                bom_lines : this.return_bom_line_data(),
                line_ref : this.get_orderline_ref(),
                state : this.state,
                priority : this.get_kitchen_item_priority() || false,
                combo_prod_info: this.get_combo_prod_info() || false,
                combo_ext_line_info : (this.product.is_combo ? combo_ext_line_info : []),
                is_main_combo_product: (this.product.is_combo ? true : false),
                tech_combo_data : (this.product.is_combo ? this.combo_prod_info : []),
            }
            $.extend(lines, new_attr);
            return lines;
        },
        get_unit: function(){
            var res = _super_orderline.get_unit.call(this);
            var unit_id = this.uom_id;
            if(!unit_id){
                return res;
            }
            unit_id = unit_id[0];
            if(!this.pos){
                return undefined;
            }
            return this.pos.units_by_id[unit_id];
        },
        is_print_serial: function() {
            var order = this.pos.get('selectedOrder');
            return order.get_print_serial();
        },
        export_for_printing: function() {
            var lines = _super_orderline.export_for_printing.call(this);
            var order = this.pos.get('selectedOrder');
            lines.original_price = this.get_original_price() || false;
            var serials = "Serial No(s).: ";
            var serials_lot = [];
            var self = this;
            if(this.pack_lot_lines && this.pack_lot_lines.models){
                _.each(this.pack_lot_lines.models,function(lot) {
                    if(lot && lot.get('lot_name')){
                        if($.inArray(lot.get('lot_name'), serials_lot) == -1){
                            var count = 0;
                            serials_lot.push(lot.get('lot_name'));
                            _.each(self.pack_lot_lines.models,function(lot1) {
                                if(lot1 && lot1.get('lot_name')){
                                    if(lot1.get('lot_name') == lot.get('lot_name')){
                                        count ++;
                                    }
                                }
                            });
                            serials += lot.get('lot_name')+"("+count+")"+", ";
                        }
                    }
                });
            } else { serials = "";}
            var new_attr = {
                line_note: this.get_line_note(),
                promotion_data: this.get_promotion_data() || false,
                serials: serials ? serials : false,
                is_print: order.get_print_serial(),
                return_valid_days: this.get_return_valid_days(),
                bom_line : this.return_bom_line_data() || false,
                combo_prod_info: this.get_combo_prod_info() || false,
            }
            $.extend(lines, new_attr);
            return lines;
        },
        get_required_number_of_lots: function(){
            var lots_required = 1;
            lots_required = this.quantity;
            return lots_required;
        },
        can_be_merged_with: function(orderline){
            var merged_lines = _super_orderline.can_be_merged_with.call(this, orderline);
            return merged_lines;
            /*if((this.get_quantity() < 0 || orderline.get_quantity() < 0)){
                return false;
            } else if(!merged_lines){
                if (!this.manual_price) {
                    if(this.get_location_id() !== this.pos.shop.id){
                        return false
                    }
                    if(this.get_promotion() && this.get_promotion().parent_product_id){
                        return false;
                    }else{
                        return (this.get_product().id === orderline.get_product().id);
                    }
                } else {
                    return false;
                }
            } else {
                if(this.get_is_rule_applied()){
                    return false;
                } else{
                    return merged_lines
                }
            }*/
        },
        merge: function(orderline){
            if (this.get_oid()/* || this.pos.get_order().get_missing_mode()*/) {
                this.set_quantity(this.get_quantity() + orderline.get_quantity() * -1);
            } else {
                _super_orderline.merge.call(this, orderline);
            }
        },
        set_promotion: function(promotion) {
            this.set('promotion', promotion);
        },
        get_promotion: function() {
            return this.get('promotion');
        },
        set_child_line_id: function(child_line_id){
            this.child_line_id = child_line_id;
        },
        get_child_line_id: function(){
            return this.child_line_id;
        },
        set_buy_x_get_dis_y: function(product_ids){
            this.product_ids = product_ids;
        },
        get_buy_x_get_dis_y: function(){
            return this.product_ids;
        },
        set_buy_x_get_y_child_item: function(buy_x_get_y_child_item){
            this.buy_x_get_y_child_item = buy_x_get_y_child_item;
        },
        get_buy_x_get_y_child_item: function(buy_x_get_y_child_item){
            return this.buy_x_get_y_child_item;
        },
        set_discount_line_id: function(discount_line_id){
            this.discount_line_id = discount_line_id;
        },
        get_discount_line_id: function(discount_line_id){
            return this.discount_line_id;
        },
        set_quantity_discount: function(quantity_discount){
            this.quantity_discount = quantity_discount;
        },
        get_quantity_discount: function(){
            return this.quantity_discount;
        },
        set_discount_amt_rule: function(discount_amt_rule){
            this.discount_amt_rule = discount_amt_rule;
        },
        get_discount_amt_rule: function(){
            return this.discount_amt_rule;
        },
        set_discount_amt: function(discount_amt){
            this.discount_amt = discount_amt;
        },
        get_discount_amt: function(){
            return this.discount_amt;
        },
        get_discount_amt_str: function(){
            return this.pos.chrome.format_currency(this.discount_amt);
        },
        set_multi_prods_line_id: function(multi_prods_line_id){
            this.multi_prods_line_id = multi_prods_line_id;
        },
        get_multi_prods_line_id: function(){
            return this.multi_prods_line_id;
        },
        set_is_rule_applied: function(is_rule_applied){
            this.is_rule_applied = is_rule_applied;
        },
        get_is_rule_applied: function(){
            return this.is_rule_applied;
        },
        set_combinational_product_rule: function(combinational_product_rule){
            this.combinational_product_rule = combinational_product_rule;
        },
        get_combinational_product_rule: function(){
            return this.combinational_product_rule;
        },
        set_multi_prod_categ_rule: function(multi_prod_categ_rule){
            this.multi_prod_categ_rule = multi_prod_categ_rule;
        },
        get_multi_prod_categ_rule: function(){
            return this.multi_prod_categ_rule;
        },
    });
    
    var _super_paymentline = models.Paymentline.prototype;
    models.Paymentline = models.Paymentline.extend({
       initialize: function(attributes, options) {
           var self = this;
           _super_paymentline.initialize.apply(this, arguments);
           this.set({
                   loyalty_point: 0,
                   loyalty_amount: 0.00,
           });
        },
        set_loyalty_point: function(points){
            this.set('loyalty_point', points)
        },
        get_loyalty_point: function(){
            return this.get('loyalty_point')
        },
        set_loyalty_amount: function(amount){
            this.set('loyalty_amount', amount)
        },
        get_loyalty_amount: function(){
            return this.get('loyalty_amount')
        },
        set_freeze_line: function(freeze_line){
            this.set('freeze_line', freeze_line)
        },
        get_freeze_line: function(){
            return this.get('freeze_line')
        },
        set_giftcard_line_code: function(gift_card_code) {
            this.gift_card_code = gift_card_code;
        },
        get_giftcard_line_code: function(){
            return this.gift_card_code;
        },
        set_freeze: function(freeze) {
            this.freeze = freeze;
        },
        get_freeze: function(){
            return this.freeze;
        },
        set_gift_voucher_line_code: function(code) {
            this.code = code;
        },
        get_gift_voucher_line_code: function(){
            return this.code;
        },
        set_pid: function(pid) {
            this.pid = pid;
        },
        get_pid: function(){
            return this.pid;
        },
        set_payment_charge: function(val){
            this.set('payment_charge',val);
        },
        get_payment_charge: function(val){
            return this.get('payment_charge');
        },
    });

});
