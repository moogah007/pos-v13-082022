odoo.define('flexibite_com_advance.chrome', function (require) {
"use strict";

    var chrome = require('point_of_sale.chrome');
    // var bus_service = require('bus.BusService');
    // var bus = require('bus.Longpolling');
    var gui = require('point_of_sale.gui');
    var PosBaseWidget = require('point_of_sale.BaseWidget');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var ActionManager = require('web.ActionManager');
    var models = require('point_of_sale.models');
    var session = require('web.session');
    // var cross_tab = require('bus.CrossTab').prototype;
    require('bus.BusService');
    var bus = require('bus.Longpolling');
    var cross_tab = require('bus.CrossTab').prototype;

    var _t = core._t;
    var QWeb = core.qweb;

    function start_lock_timer(time_interval,self){
        var $area = $(document),
        idleActions = [{
            milliseconds: time_interval * 100000,
            action: function () {
                var params = {
                    model: 'pos.session',
                    method: 'write',
                    args: [self.pos.pos_session.id,{'is_lock_screen' : true}],
                }
                rpc.query(params, {async: false}).then(function(result){}).catch(function(){
                    self.pos.db.notification('danger',"Connection lost");
                });
                // $('.lock_button').css('background-color', 'rgb(233, 88, 95)');
                $('.freeze_screen').addClass("active_state");
                $(".unlock_button").fadeIn(2000);
                $('.unlock_button').show();
                $('.unlock_button').css('z-index',10000);
            }
        }];
        function lock (event, times, undefined) {
            var idleTimer = $area.data('idleTimer');
            if (times === undefined) times = 0;
            if (idleTimer) {
                clearTimeout($area.data('idleTimer'));
            }
            if (times < idleActions.length) {
                $area.data('idleTimer', setTimeout(function () {
                    idleActions[times].action();
                    lock(null, ++times);
                }, idleActions[times].milliseconds));
            } else {
                $area.off('mousemove click', lock);
            }
        };
        $area
            .data('idle', null)
            .on('mousemove click', lock);
        lock(); 
    }

    chrome.Chrome.include({
        events: {
            "click #product_sync": "product_sync",
            "click #pos_lock": "pos_lock",
            "click #messages_button": "messages_button",
            "click #close_draggable_panal": "close_draggable_panal",
            "click #delete_msg_history": "delete_msg_history",
            "click #sale_note_chrome": "sale_note_chrome",
            "click #delivery_list_chrome": "delivery_list_chrome",
            "click #close_draggable_panal_delivery_order" :"close_draggable_panal_delivery_order",
            'click #pay_quick_order' : "pay_quick_draft_order",
            "click .close_incoming_order_panel" :"close_incoming_order_panel",
            "click #sale_person_chrome" :"select_pos_sale_person",
        },
        select_pos_sale_person: function(){
            var self = this;
            var sales_person_list = [];
            for (var i = 0; i < this.pos.users.length; i++) {
                var user = this.pos.users[i];
                if(self.pos.get_cashier() && self.pos.get_cashier().id != user.id){
                    sales_person_list.push({
                        'label': user.name,
                        'item':  user,
                    });
                }
            }
            self.gui.show_popup('assign_sales_person_popup',{
                title: _t('Assign Sales Person'),
                salesperson_list: sales_person_list,
                is_selected: function(user){
                    var selectedOrder = self.pos.get_order();
                    if(user && user.id && selectedOrder.get_salesman_id()){
                        if(user.id == selectedOrder.get_salesman_id()){
                            return user.id;
                        }
                    } else{
                        return
                    }
                }
            });
        },
        delivery_list_chrome: function(){
            var self = this;
            if($('#draggablePanelList_delivery_order').css('display') == 'none'){
                $('#draggablePanelList_delivery_order').animate({
                    height: 'toggle'
                    }, 200, function() {
                });
                var delivery_orders = _.filter(self.pos.get('pos_order_list'), function(item) {
                     return item.delivery_type == 'pending'
                });
                self.render_delivery_order_list(delivery_orders);
                $('#head_data_delivery_orders').text(_t("Delivery Orders"));
            } else{
                $('#draggablePanelList_delivery_order').animate({
                    height: 'toggle'
                    }, 200, function() {
                });
            }
        },
        close_draggable_panal_delivery_order(){
            $('#draggablePanelList_delivery_order').animate({
                height: 'toggle'
                }, 200, function() {
            });
        },
        close_incoming_order_panel: function(){
            $('#draggablePanelList_sale_note').animate({
                height: 'toggle'
                }, 200, function() {
            });
        },
        product_sync: function(){
            var self = this;
            self.pos.load_new_products();
            $('.prodcut_sync').toggleClass('rotate', 'rotate-reset');
        },
        sale_note_chrome: function(){
            var self = this;
            if($('#draggablePanelList_sale_note.draft_order').css('display') == 'none'){
                $('#draggablePanelList_sale_note.draft_order').animate({
                    height: 'toggle'
                    }, 200, function() {
                });
                var draft_orders = _.filter(self.pos.get('pos_order_list'), function(item) {
                     return item.state == 'draft'
                });
                self.render_sale_note_order_list(draft_orders);
                $('#draggablePanelList_sale_note.draft_order .head_data_sale_note').html(_t("Orders"));
                $('#draggablePanelList_sale_note.draft_order .panel-body').html("Message-Box Empty");
            }else{
                $('#draggablePanelList_sale_note.draft_order').animate({
                    height: 'toggle'
                    }, 200, function() {
                });
            }
        },
        sale_note_chrome: function(){
            var self = this;
            if($('#draggablePanelList_sale_note.draft_order').css('display') == 'none'){
                $('#draggablePanelList_sale_note.draft_order').animate({
                    height: 'toggle'
                    }, 200, function() {
                });
                var draft_orders = _.filter(self.pos.get('pos_order_list'), function(item) {
                     return item.state == 'draft'
                });
                self.render_sale_note_order_list(draft_orders);
                $('#draggablePanelList_sale_note.draft_order .head_data_sale_note').html(_t("Orders"));
                $('#draggablePanelList_sale_note.draft_order .panel-body').html("Message-Box Empty");
            }else{
                $('#draggablePanelList_sale_note.draft_order').animate({
                    height: 'toggle'
                    }, 200, function() {
                });
            }
        },
        pay_quick_draft_order: function(event){
            self = this;
            var order_id = parseInt($(event.currentTarget).data('id'));
            self.pos.gui.screen_instances.orderlist.pay_order_due(false, order_id);
            self.pos.chrome.close_incoming_order_panel()
        },
        build_widgets: function(){
            var self = this;
            var partner = self.pos.config.default_partner_id;
            if(partner && self.pos.get_cashier() && self.pos.get_cashier().access_default_customer){
               var set_partner = self.pos.db.get_partner_by_id(partner[0])
                if(set_partner){
                    self.pos.get_order().set_client(set_partner);
                }
            } else if(self.pos && self.pos.get_order()){
               self.pos.get_order().set_client(null);
            }
            this._super();
            if(!self.pos.is_rfid_login){
                $('.page-container').css({
                    'width':'100%',
                });
            }
            self.slider_widget = new SliderWidget(this);
            self.pos_cart_widget = new PosCartCountWidget(this);
            self.slider_widget.replace(this.$('.placeholder-SliderWidget'));
            self.pos_cart_widget.replace(this.$('.placeholder-PosCartCountWidget'));
            self.gui.set_startup_screen('bite_login_screen');
            self.gui.show_screen('bite_login_screen');
            // this.call('bus_service', 'updateOption','lock.data',session.uid);
            // this.call('bus_service', 'onNotification', self, self._onNotification);
            // self.call('bus_service', 'updateOption','lock.data',session.uid);
            // self.call('bus_service', 'startPolling');
            // self.call('bus_service', 'onNotification', self, self._onNotification);
            // self.call('bus_service', 'startPolling');

            self.call('bus_service', 'updateOption','pos.order.line',session.uid);
            self.call('bus_service', 'startPolling');
            self.call('bus_service', 'onNotification', self, self._onNotification);
            self.call('bus_service', 'startPolling');
            cross_tab._isRegistered = true;self.call('bus_service', '_poll');
            cross_tab._isMasterTab = true;
            self.call('bus_service', '_poll');
         //    this.call('bus_service', 'startPolling');
            // this.call('bus_service', '_poll');

            if(self.pos.user.pos_user_type === 'cook'){
                self.gui.set_startup_screen('kitchen_screen');
                self.gui.show_screen('kitchen_screen');
            }
        },
        save_receipt_for_reprint:function(){
            var self = this;
            var order = this.pos.get_order();
            var env = {
                widget:self,
                pos: this.pos,
                order: order,
                receipt: order.export_for_printing(),
                orderlines: order.get_orderlines(),
                paymentlines: order.get_paymentlines(),
            };
            var receipt_html = QWeb.render('OrderReceipt',env);
            order.set_pos_normal_receipt_html(receipt_html.replace(/<img[^>]*>/g,"").replace(/<object[^>]*>/g,""));
//        	var receipt = QWeb.render('XmlReceipt',env);
//        	order.set_pos_xml_receipt_html(receipt.replace(/<img[^>]*>/g,"").replace(/<object[^>]*>/g,""));
        },
        _onNotification: function(notifications){
            var self = this;
            for (var notif of notifications) {
                if(notif[1] && notif[1].terminal_lock){
                    if(notif[1].terminal_lock[0]){
                        if(self.pos.pos_session && (notif[1].terminal_lock[0].session_id[0] == self.pos.pos_session.id)){
                            self.pos.set_lock_status(notif[1].terminal_lock[0].lock_status);
                            self.pos.set_lock_data(notif[1].terminal_lock[0]);
                        }
                    }
                } else if(notif[1] && notif[1].terminal_message){
                    if(notif[1].terminal_message[0]){
                        if(self.pos.pos_session.id == notif[1].terminal_message[0].message_session_id[0]){
                            var message_index = _.findIndex(self.pos.message_list, function (message) {
                                return message.id === notif[1].terminal_message[0].id;
                            });
                            if(message_index == -1){
                                self.pos.message_list.push(notif[1].terminal_message[0]);
                                self.render_message_list(self.message_list);
                                $('#message_icon').css("color", "#5EB937");
                                self.pos.db.notification('info',notif[1].terminal_message[0].sender_user[1]+' has sent new message.');
                            }
                        }
                    }
                } else if(notif[1] && notif[1].rating){
                    var order = self.pos.get_order();
                    if(order){
                        order.set_rating(notif[1].rating);
                    }
                }else if(notif[1] && notif[1].screen_display_data){
                    if(notif[1].screen_display_data.new_order){
                        self.gui.play_sound('bell');
                    }
                    var screen_data = [];
                    _.each(notif[1].screen_display_data.orders,function(order){
                        _.each(order.order_lines,function(line){
                            if(line.state != 'done' && line.state != 'cancel'){
                                screen_data.push(line);
                            }
                        });
                    });
                    this.pos.set('screen_data',screen_data);
                    var screen_order_lines = [];
                    var categ_id = 0
                    if(self.chrome && self.chrome.screens && self.chrome.screens.kitchen_screen){
                        categ_id = self.chrome.screens.kitchen_screen.categ_id;
                    }
                    _.each(notif[1].screen_display_data.orders,function(order){
                        _.each(order.order_lines,function(line){
                            if(categ_id == 0 && line.state != 'done' && line.state != 'cancel'){
                                screen_order_lines.push(line);
                            }else if(line.categ_id == categ_id && line.state != 'done' && line.state != 'cancel'){
                                 screen_order_lines.push(line);
                            }
                        });
                    });
                    if(self.chrome && self.chrome.screens && self.chrome.screens.kitchen_screen){
                        self.chrome.screens.kitchen_screen.render_screen_order_lines(screen_order_lines);
                        self.chrome.screens.kitchen_screen.render_table_data(notif[1].screen_display_data.orders);
                    }
                } else if(notif[1] && notif[1].partner_id){
                    var partner_id = notif[1].partner_id;
                    var partner = self.pos.db.get_partner_by_id(partner_id);
                    var order = self.pos.get_order();
                    if(partner){
                        if(order){
                            order.set_client(partner);
                        }
                    }else{
                        if(partner_id){
                            var params = {
                                model: 'res.partner',
                                method: 'search_read',
                                domain: [['id','=',partner_id]],
                            }
                            rpc.query(params, {async: false})
                            .then(function(partner){
                                if(partner && partner.length > 0){
                                    self.pos.db.add_partners(partner);
                                    order.set_client(partner[0]);
                                }else{
                                    self.pos.db.notification('danger',"Customer not loaded in POS.");
                                }
                            });
                        }
                    }
                } else if(notif[1] && notif[1].new_pos_order){
                    var previous_sale_note = self.pos.get('pos_order_list');
                    if(notif[1].new_pos_order[0].state == "paid"){
                            self.pos.db.notification('success',_t(notif[1].new_pos_order[0].display_name + ' order has been paid.'));
                        } else{
                            self.pos.db.notification('success',_t(notif[1].new_pos_order[0].display_name + ' order has been created.'));
                        }
                    previous_sale_note.push(notif[1].new_pos_order[0]);
                    var obj = {};
                    for ( var i=0, len=previous_sale_note.length; i < len; i++ ){
                        obj[previous_sale_note[i]['id']] = previous_sale_note[i];
                    }
                    previous_sale_note = new Array();
                    for ( var key in obj ){
                         previous_sale_note.push(obj[key]);
                    }
                    previous_sale_note.sort(function(a, b) {
                        return b.id - a.id;
                    });
                    self.pos.db.add_orders(previous_sale_note);
                    self.pos.set({'pos_order_list':previous_sale_note});
                    if(self && self.chrome && self.chrome.screens && self.chrome.screens.orderlist){
                        self.pos.chrome.screens.orderlist.render_list(previous_sale_note);
                    }
                    self.render_sale_note_order_list(previous_sale_note);
                } else if(notif[1] && notif[1].edited_pos_order){
                    var previous_sale_note = self.pos.get('pos_order_list');
                    self.pos.db.notification('success',' Order has been updated:' + _t(notif[1].edited_pos_order[0].display_name));
                    var updated_order_list = _.without(previous_sale_note, _.findWhere(previous_sale_note, {'id': notif[1].edited_pos_order.id}));
                    updated_order_list.push(notif[1].edited_pos_order[0]);
                    var obj = {};
                    for ( var i=0, len=updated_order_list.length; i < len; i++ ){
                        obj[updated_order_list[i]['id']] = updated_order_list[i];
                    }
                    updated_order_list = new Array();
                    for ( var key in obj ){
                        updated_order_list.push(obj[key]);
                    }
                    updated_order_list.sort(function(a, b) {
                        return b.id - a.id;
                    });
                    self.pos.db.add_orders(updated_order_list);
                    self.pos.set({'pos_order_list':updated_order_list});
                    if(self && self.chrome && self.chrome.screens && self.chrome.screens.orderlist){
                        self.pos.chrome.screens.orderlist.render_list(updated_order_list);
                    }
                    self.render_sale_note_order_list(updated_order_list);
                } else if(notif[1] && notif[1].sync_order_paid){
                    var previous_sale_note = self.pos.get('pos_order_list');
                    self.pos.db.notification('success',_t(notif[1].sync_order_paid[0].display_name) + 'Order has been paid');
                    var updated_order_list = _.without(previous_sale_note, _.findWhere(previous_sale_note, {'id': notif[1].sync_order_paid.id}));
                    updated_order_list.push(notif[1].sync_order_paid[0]);
                    var obj = {};
                    for ( var i=0, len=updated_order_list.length; i < len; i++ ){
                        obj[updated_order_list[i]['id']] = updated_order_list[i];
                    }
                    updated_order_list = new Array();
                    for ( var key in obj ){
                        updated_order_list.push(obj[key]);
                    }
                    updated_order_list.sort(function(a, b) {
                        return b.id - a.id;
                    });
                    self.pos.db.add_orders(updated_order_list);
                    self.pos.set({'pos_order_list':updated_order_list});
                    if(self && self.chrome && self.chrome.screens && self.chrome.screens.orderlist){
                        self.pos.chrome.screens.orderlist.render_list(updated_order_list);
                    }
                    self.render_sale_note_order_list(updated_order_list);
                } else if(notif[1] && notif[1].delivery_pos_order   ){
                    var existing_orders = self.pos.get('pos_order_list');
                    var filtered = _.filter(existing_orders, function(item) {
                        return item.id !== notif[1].delivery_pos_order[0].id
                    });
                    filtered.push(notif[1].delivery_pos_order[0]);
                    filtered = _.sortBy(filtered, 'id').reverse();
                    self.pos.db.add_orders(filtered);
                    self.pos.set({'pos_order_list':filtered});
                    var delivery_orders = _.filter(self.pos.get('pos_order_list'), function(item) {
                         return item.delivery_type == 'pending'
                    });
                    self.render_delivery_order_list(delivery_orders);
                }
            }
        },
        render_sale_note_order_list: function(orders){
            var self = this;
            if(orders){
                var contents = $('.message-panel-body1');
                contents.html("");
                var order_count = 0;
                for(var i = 0, len = Math.min(orders.length,1000); i < len; i++){
                    var order    = orders[i];
                    if(order.state == "draft"){
                        order_count ++;
                        var orderlines = [];
                        order.amount_total = parseFloat(order.amount_total).toFixed(2);
                        var clientline_html = QWeb.render('SaleNoteQuickWidgetLine',{widget: this, order:order, orderlines:orderlines});
                        var clientline = document.createElement('tbody');
                        clientline.innerHTML = clientline_html;
                        clientline = clientline.childNodes[1];
                        contents.append(clientline);
                    }
                }
                self.pos.order_quick_draft_count = order_count
                $('.notification-count').show();
                $('.draft_order_count').text(order_count);
            }
        },
        render_delivery_order_list: function(orders){
            var self = this;
            if(orders){
                var contents = $('.message-panel-body2');
                contents.html("");
                var order_count = 0;
                for(var i = 0, len = Math.min(orders.length,1000); i < len; i++){
                    var order = orders[i];
                    order_count ++;
                    var orderlines = [];
                    order.amount_total = parseFloat(order.amount_total).toFixed(2);
                    var clientline_html = QWeb.render('DeliveryOrdersQuickWidgetLine',{widget: this, order:order, orderlines:orderlines});
                    var clientline = document.createElement('tbody');
                    clientline.innerHTML = clientline_html;
                    clientline = clientline.childNodes[1];
                    contents.append(clientline);
                }
                self.pos.delivery_order_count = order_count
//            	$('.notification-count').show();
                $('.delivery_order_count').text(order_count);
            }
        },
        pos_lock: function(){
            var self = this;
            self.pos.session_by_id = {};
            var domain = [['state','=', 'opened'],['id','!=',self.pos.pos_session.id]];
            var params = {
                model: 'pos.session',
                method: 'search_read',
                domain: domain,
            }
            rpc.query(params, {async: false}).then(function(sessions){
                if(sessions && sessions.length > 0){
                    _.each(sessions,function(session){
                        self.pos.session_by_id[session.id] = session;
                    });
                    self.pos.gui.show_popup('terminal_list',{'sessions':sessions});
                } else{
                    self.pos.db.notification('danger',_t('Active sessions not found!'));
                }
            }).catch(function(){
                self.pos.db.notification('danger',"Connection lost");
            });
        },
        messages_button: function(){
            var self = this;
            if($('#draggablePanelList').css('display') == 'none'){
                $('#draggablePanelList').animate({
                    height: 'toggle'
                    }, 200, function() {
                });
                self.render_message_list(self.pos.message_list);
                $('.panel-body').css({'height':'auto','max-height':'242px','min-height':'45px','overflow':'auto'});
                $('.head_data').html(_t("Message"));
                $('.panel-body').html("Message-Box Empty");
            }else{
                $('#draggablePanelList').animate({
                    height: 'toggle'
                    }, 200, function() {
                });
            }
        },
        close_draggable_panal:function(){
            $('#draggablePanelList').animate({
                height: 'toggle'
                }, 200, function() {
            });
        },
        delete_msg_history: function(){
            var self = this;
            var params = {
                model: 'message.terminal',
                method: 'delete_user_message',
                args: [self.pos.pos_session.id],
            }
            rpc.query(params, {async: false}).then(function(result){
                if(result){
                    self.pos.message_list = []
                    self.render_message_list(self.pos.message_list)
                }
            }).fail(function(){
                self.pos.db.notification('danger',"Connection lost");
            });
        },
        render_message_list: function(message_list){
            var self = this;
            if(message_list && message_list[0]){
                var contents = $('.message-panel-body');
                contents.html("");
                var temp_str = "";
                for(var i=0;i<message_list.length;i++){
                    var message = message_list[i];
                    var messageline_html = QWeb.render('MessageLine',{widget: this, message:message_list[i]});
                    temp_str += messageline_html;
                }
                contents.html(temp_str)
                $('.message-panel-body').scrollTop($('.message-panel-body')[0].scrollHeight);
                $('#message_icon').css("color", "gray");
            } else{
                var contents = $('.message-panel-body');
                contents.html("");
            }
        },
        user_icon_url(id){
            return '/web/image?model=res.users&id='+id+'&field=image_128';
        },
    });

    var SliderWidget = PosBaseWidget.extend({
        template: 'SliderWidget',
        init: function(parent, options){
            var self = this;
            this._super(parent,options);
            self.click_username = function(){
                self.pos.get_order().destroy();
                self.gui.show_screen('bite_login_screen');
//                self.gui.select_user({
//                    'security':     true,
//                    'current_user': self.pos.get_cashier(),
//                    'title':      _t('Change Cashier'),
//                }).then(function(user){
//                    self.pos.set_cashier(user);
//                    self.renderElement();
//                });
            };
            self.sidebar_button_click = function(){
                if(self.gui.get_current_screen() !== "receipt"){
                    $(this).parent().removeClass('oe_hidden');
                    $(this).parent().toggleClass("toggled");
                    $(this).find('i').toggleClass('fa fa-chevron-right fa fa-chevron-left');
                }
            };
            self.all_sale_orders = function(){
                self.gui.show_screen('saleorderlist');
                self.close_sidebar();
            },
            self.sale_invoice = function(){
                self.gui.show_screen('invoice_list');
                self.close_sidebar();
            },
            self.open_product_screen = function(){
                self.gui.show_screen('product-screen');
                self.close_sidebar();
            };
            self.open_sales_deshboard = function(){
                self.gui.show_screen('pos_dashboard_graph_view');
                self.close_sidebar();
            },
            self.open_expiry_deshboard = function(){
                self.gui.show_screen('product_expiry_deshboard');
                self.close_sidebar();
            },
            self.gift_card_screen = function(){
                self.close_sidebar();
                self.gui.show_screen('giftcardlistscreen');
            };
            self.discard_product_screen = function(){
                self.close_sidebar();
                self.gui.show_screen('stockpickinglistscreen');
            },
            self.gift_voucher_screen = function(){
                self.close_sidebar();
                self.gui.show_screen('voucherlistscreen');
            };
            self.open_order_screen = function(){
                self.gui.show_screen('orderlist');
                self.close_sidebar();
            };
            self.out_of_stock_detail = function(){
                self.gui.show_screen('product-out-of-stock');
                self.close_sidebar();
            };
            self.user_change_pin = function(){
                self.gui.show_popup('change_user_pin_popup');
                self.close_sidebar();
            },
            self.internal_stock_transfer = function(){
                var selectedOrder = self.pos.get_order();
                var currentOrderLines = selectedOrder.get_orderlines();
                if(self.pos.stock_pick_typ.length == 0){
                    return alert(_t("You can not proceed with 'Manage only 1 Warehouse with only 1 stock location' from inventory configuration."));
                }
                if(currentOrderLines.length == 0){
                    return alert(_t("You can not proceed with empty cart."));
                }
                self.gui.show_popup('int_trans_popup',{'stock_pick_types':self.pos.stock_pick_typ,'location':self.pos.location_ids});
            };
            self.print_lastorder = function(){
                self.close_sidebar();
                if(self.pos.get('pos_order_list').length > 0){
                    var last_order_id = Math.max.apply(Math,self.pos.get('pos_order_list').map(function(o){return o.id;}))
                    var result;
                    _.each(self.pos.get('pos_order_list'),function(item) {
                        if(item.id == last_order_id){
                            result = item;
                        }
                    });
                    var selectedOrder = self.pos.get_order();
                    var currentOrderLines = selectedOrder.get_orderlines();
                    if(currentOrderLines.length > 0) {
                        selectedOrder.set_order_id('');
                        for (var i=0; i <= currentOrderLines.length + 1; i++) {
                            _.each(currentOrderLines,function(item) {
                                selectedOrder.remove_orderline(item);
                            });
                        }
                        selectedOrder.set_client(null);
                    }
                    if(result && result.pos_normal_receipt_html){
                        selectedOrder.print_receipt_html = result.pos_normal_receipt_html;
                        selectedOrder.print_xml_receipt_html = result.pos_xml_receipt_html;
                        selectedOrder.is_reprint = true;
                        selectedOrder.name = result.pos_reference;
                        self.gui.show_screen('receipt');
                    }





                    // if (result && result.lines.length > 0) {
                    //     partner = null;
                    //     if (result.partner_id && result.partner_id[0]) {
                    //         var partner = self.pos.db.get_partner_by_id(result.partner_id[0])
                    //     }
                    //     selectedOrder.set_amount_paid(result.amount_paid);
                    //     selectedOrder.set_amount_return(Math.abs(result.amount_return));
                    //     selectedOrder.set_amount_tax(result.amount_tax);
                    //     selectedOrder.set_amount_total(result.amount_total);
                    //     selectedOrder.set_company_id(result.company_id[1]);
                    //     selectedOrder.set_date_order(result.date_order);
                    //     selectedOrder.set_client(partner);
                    //     selectedOrder.set_pos_reference(result.pos_reference);
                    //     selectedOrder.set_user_name(result.user_id && result.user_id[1]);
                    //     selectedOrder.set_order_note(result.note);
                    //     selectedOrder.set_delivery_date(result.delivery_date);
                    //     selectedOrder.set_delivery_address(result.delivery_address);
                    //     selectedOrder.set_delivery_time(result.delivery_time);
                    //     selectedOrder.set_delivery_type(result.delivery_type);
                    //     selectedOrder.set_delivery_user_id(result.delivery_user_id[0]);
                    //     var statement_ids = [];
                    //     if (result.statement_ids) {
                    //     	var params = {
                    //     		model: 'account.bank.statement.line',
                    //     		method: 'search_read',
                    //     		domain: [['id', 'in', result.statement_ids]],
                    //     	}
                    //     	rpc.query(params, {async: false}).then(function(st){
                    //     		if (st) {
                    //         		_.each(st, function(st_res){
                    //                 	var pymnt = {};
                    //                 	pymnt['amount']= st_res.amount;
                    //                     pymnt['journal']= st_res.journal_id[1];
                    //                     statement_ids.push(pymnt);
                    //         		});
                    //             }
                    //     	}).fail(function(){
                    //         	self.pos.db.notification('danger',"Connection lost");
                    //         });
                    //         selectedOrder.set_journal(statement_ids);
                    //     }
                    //     var params = {
                    // 		model: 'pos.order.line',
                    // 		method: 'search_read',
                    // 		domain: [['id', 'in', result.lines]],
                    // 	}
                    // 	rpc.query(params, {async: false}).then(function(lines){
                    // 		if (lines) {
                    //         	_.each(lines, function(line){
                    //                 var product = self.pos.db.get_product_by_id(Number(line.product_id[0]));
                    //                 var _line = new models.Orderline({}, {pos: self.pos, order: selectedOrder, product: product});
                    //                 _line.set_discount(line.discount);
                    //                 _line.set_quantity(line.qty);
                    //                 _line.set_unit_price(line.price_unit)
                    //                 _line.set_line_note(line.line_note);
                    //                 _line.set_bag_color(line.is_bag);
                    //                 _line.set_return_valid_days(line.return_valid_days);
                    //                 _line.set_deliver_info(line.deliver);
                    //                 if(line && line.is_delivery_product){
                    //                 	_line.set_delivery_charges_color(true);
                    //                 	_line.set_delivery_charges_flag(true);
                    //                 }
                    //                 selectedOrder.add_orderline(_line);
                    //         	});
                    //         }
                    // 	}).fail(function(){
                    //     	self.pos.db.notification('danger',"Connection lost");
                    //     });
                    //     if(self.pos.config.iface_print_via_proxy){
                    //         var receipt = selectedOrder.export_for_printing();
                    //         var env = {
                    //                 receipt: receipt,
                    //                 widget: self,
                    //                 pos: self.pos,
                    //                 order: self.pos.get_order(),
                    //                 paymentlines: self.pos.get_order().get_paymentlines()
                    //             }
                    //             self.pos.proxy.print_receipt(QWeb.render('XmlReceipt',env));
                    //         self.pos.get('selectedOrder').destroy();    //finish order and go back to scan screen
                    //     }else{
                    //     	self.gui.show_screen('receipt');
                    //     }
                    // }
                } else {
                    self.pos.db.notification('danger',_t("No order to print."));
                }
            };
            self.pos_graph = function(){
                self.gui.show_screen('graph_view');
                self.close_sidebar();
            };
            self.x_report = function(){
                var pos_session_id = [self.pos.pos_session.id];
                self.pos.chrome.do_action('flexibite_com_advance.pos_x_report',{additional_context:{
                    active_ids:pos_session_id,
                }}).catch(function(){
                    self.pos.db.notification('danger',"Connection lost");
                });
                /*if(self.pos.config.iface_print_via_proxy){
                    var pos_session_id = self.pos.pos_session.id;
                    var report_name = "flexibite_com_advance.pos_x_thermal_report_template";
                    var params = {
                        model: 'ir.actions.report',
                        method: 'get_html_report',
                        args: [pos_session_id, report_name],
                    }
                    rpc.query(params, {async: false})
                    .then(function(report_html){
                        if(report_html && report_html[0]){
                            self.pos.proxy.print_receipt(report_html[0]);
                        }
                    });
                }*/
                self.close_sidebar();
            };
            self.payment_summary_report = function(){
                self.close_sidebar();
                self.gui.show_popup('payment_summary_report_wizard');
            };
            self.product_summary_report = function(){
                self.close_sidebar();
                self.gui.show_popup('product_summary_report_wizard');
            };
            self.order_summary_report = function(){
                self.close_sidebar();
                self.gui.show_popup('order_summary_popup');
            };
            self.print_audit_report = function(){
                self.close_sidebar();
                self.gui.show_popup('report_popup');
            };
            self.cash_in_out_stmt = function(){
                self.close_sidebar();
                self.gui.show_popup('cash_inout_statement_popup');
            };
            self.credit_debit_stmt = function(){
                var order = self.pos.get_order();
                if(order.get_client() && order.get_client().name){
                    self.gui.show_popup('credit_debit_statement_popup');
                    self.close_sidebar();
                    order.set_ledger_click(true);
                }else{
                    self.gui.show_screen('clientlist');
                }
            };
//	    	self.delivery_details_screen = function(){
//        		self.gui.show_screen('delivery_details_screen');
//        		self.close_sidebar();
//        	},
            self.today_sale_report = function(){
                self.close_sidebar();
                var str_payment = '';
                var params = {
                    model: 'pos.session',
                    method: 'get_session_report',
                    args: [],
                }
                rpc.query(params, {async: false}).then(function(result){
                    if(result['error']){
                        self.pos.db.notification('danger',result['error']);
                    }
                    if(result['payment_lst']){
                        var temp = [] ;
                        for(var i=0;i<result['payment_lst'].length;i++){
                            if(result['payment_lst'][i].session_name){
                                if(jQuery.inArray(result['payment_lst'][i].session_name,temp) != -1){
                                    str_payment+="<tr><td style='font-size: 16px;padding: 8px;'>"+result['payment_lst'][i].journals+"</td>" +
                                    "<td style='font-size: 16px;padding: 8px;'>"+self.format_currency(result['payment_lst'][i].total.toFixed(2))+"</td>" +
                                "</tr>";
                                }else{
                                    str_payment+="<tr><td style='font-size:14px;padding: 8px;' colspan='2'>"+result['payment_lst'][i].session_name+"</td></tr>"+
                                    "<td style='font-size: 16px;padding: 8px;'>"+result['payment_lst'][i].journals+"</td>" +
                                    "<td style='font-size: 16px;padding: 8px;'>"+self.format_currency(result['payment_lst'][i].total.toFixed(2))+"</td>" +
                                "</tr>";
                                temp.push(result['payment_lst'][i].session_name);
                                }
                            }
                        }
                    }
                    self.gui.show_popup('pos_today_sale',{result:result,str_payment:str_payment});
                }).catch(function(){
                    self.pos.db.notification('danger',"Connection lost");
                });
            };
        },
        close_sidebar: function(){
            $("#wrapper").addClass('toggled');
            $('#wrapper').find('i').toggleClass('fa fa-chevron-left fa fa-chevron-right');
        },
        renderElement: function(){
            var self = this;
            self._super();
            self.el.querySelector('#side_username').addEventListener('click', self.click_username);
            self.el.querySelector('#slidemenubtn').addEventListener('click', self.sidebar_button_click);
            self.el.querySelector('a#product-screen').addEventListener('click', self.open_product_screen);
            if(self.pos.config.product_expiry_report && self.pos.get_cashier().access_product_expiry_report){
                self.el.querySelector('li.expiry_deshboard').addEventListener('click', self.open_expiry_deshboard);
            }
            if(self.pos.config.sale_order_operations && self.pos.config.pos_sale_order){
                self.el.querySelector('a#all_sale_orders').addEventListener('click', self.all_sale_orders);
            }
            if(self.pos.config.sale_order_invoice && self.pos.config.pos_sale_order){
                self.el.querySelector('a#all_sale_invoice').addEventListener('click', self.sale_invoice);
            }
            if(self.pos.config.pos_dashboard && self.pos.get_cashier().access_pos_dashboard){
                self.el.querySelector('li.sales_deshboard').addEventListener('click', self.open_sales_deshboard);
            }
            if(self.pos.config.enable_gift_card && self.pos.get_cashier().access_gift_card){
                self.el.querySelector('a#gift_card_screen').addEventListener('click', self.gift_card_screen);
            }
            if(self.pos.config.discard_product && self.pos.get_cashier().discard_product){
                self.el.querySelector('a#discard_product_screen').addEventListener('click', self.discard_product_screen);
            }
            if(self.pos.config.enable_gift_voucher && self.pos.get_cashier().access_gift_voucher){
                self.el.querySelector('a#gift_voucher_screen').addEventListener('click', self.gift_voucher_screen);
            }
            if(self.pos.config.enable_reorder && self.pos.get_cashier().access_reorder){
                self.el.querySelector('a#order-screen').addEventListener('click', self.open_order_screen);
            }
            if(self.pos.config.out_of_stock_detail){
                self.el.querySelector('a#out_of_stock').addEventListener('click', self.out_of_stock_detail);
            }
            if(self.pos.config.enable_int_trans_stock){
                self.el.querySelector('a#stock_transfer').addEventListener('click', self.internal_stock_transfer);
            }
            if(self.pos.config.enable_print_last_receipt && self.pos.get_cashier().access_print_last_receipt){
                self.el.querySelector('a#print_lastorder').addEventListener('click', self.print_lastorder);
            }
            if(self.el.querySelector('li.pos-graph')){
                self.el.querySelector('li.pos-graph').addEventListener('click', self.pos_graph);
            }
            if(self.el.querySelector('li.x-report')){
                self.el.querySelector('li.x-report').addEventListener('click', self.x_report);
            }
            if(self.el.querySelector('li.today_sale_report')){
                self.el.querySelector('li.today_sale_report').addEventListener('click', self.today_sale_report);
            }
            if(self.el.querySelector('li.payment_summary_report')){
                self.el.querySelector('li.payment_summary_report').addEventListener('click', self.payment_summary_report);
            }
            if(self.el.querySelector('li.product_summary_report')){
                self.el.querySelector('li.product_summary_report').addEventListener('click', self.product_summary_report);
            }
            if(self.el.querySelector('li.order_summary_report')){
                self.el.querySelector('li.order_summary_report').addEventListener('click', self.order_summary_report);
            }
            if(self.el.querySelector('li.print_audit_report')){
                self.el.querySelector('li.print_audit_report').addEventListener('click', self.print_audit_report);
            }
            if(self.el.querySelector('li.cash_in_out_stmt')){
                self.el.querySelector('li.cash_in_out_stmt').addEventListener('click', self.cash_in_out_stmt);
            }
            if(self.el.querySelector('li.credit_debit_stmt')){
                self.el.querySelector('li.credit_debit_stmt').addEventListener('click', self.credit_debit_stmt);
            }
//        	if(self.pos.config.enable_delivery_charges && self.pos.get_cashier().access_delivery_charges){
//        	    self.el.querySelector('a#delivery_details_screen').addEventListener('click', self.delivery_details_screen);
//        	}
            if(self.pos.config.enable_change_pin){
                self.el.querySelector('a#user_change_pin').addEventListener('click', self.user_change_pin);
            }
            $('.main_slider-ul').click(function() {
                $(this).find('ul.content-list-ul').slideToggle();
            });
        },
    });

    var PosCartCountWidget = PosBaseWidget.extend({
        template: 'PosCartCountWidget',
        init: function(parent, options){
            var self = this;
            this._super(parent,options);
            self.show_cart = function(){
                var order = self.pos.get_order();
                if(order.is_empty()) {
                    return;
                }
                if(self.gui.get_current_screen() != 'products'){
                    var html_data = $('.order-scroller').html();
                    $('.show-left-cart').html('').append(html_data);
                    $('.show-left-cart').toggle("slide");
                }
            };
        },
        renderElement: function(){
            var self = this;
            self._super();
            $(".pos-cart-info").delegate( "#pos-cart", "click",self.show_cart);
        },
    });

    /*chrome.HeaderButtonWidget.include({
        renderElement: function(){
            var self = this;
            this._super();
            if(this.action){
                this.$el.click(function(){
                    self.gui.show_popup('POS_session_config');
                });
            }
        },
    });*/

    /* ********************************************************
Define: pos_product_template.VariantListWidget

- This widget will display a list of Variants;
- This widget has some part of code that come from point_of_sale.ProductListWidget;
*********************************************************** */

    var VariantListWidget = PosBaseWidget.extend({
        template:'VariantListWidget',

        init: function(parent, options) {
            var self = this;
            this._super(parent, options);
            this.variant_list = [];
            this.filter_variant_list = [];
            this.filters = {};
            this.click_variant_handler = function(event){
                var variant = self.pos.db.get_product_by_id(this.dataset['variantId']);
                if(variant.to_weight && self.pos.config.iface_electronic_scale){
                    self.__parentedParent.hide();
                    self.pos_widget.screen_selector.set_current_screen('scale',{product: variant});
                }else{
                    if(variant){
                        if(self.variant_info && self.variant_info.length > 0){
                            self.variant_info.map(function(variant){
                                variant['is_selected'] = false;
                            });
                        }
                        variant['is_selected'] = true;
                        self.update_variant_cart(variant);
                    }
                }
            };
        },
        update_variant_cart: function(variant){
            var self = this;
            var order = self.pos.get_order();
            if(order && variant){
                var vals = {
                    'id':variant.id,
                    'display_name':variant.display_name,
                    'image':self.get_product_image_url(variant),
                    'modifiers':variant.modifiers || false,
                    'qty':1,
                    'is_selected':variant.is_selected || false,
                };
                if(!self.variant_info || self.variant_info.length <= 0){
                    self.variant_info = [vals];
                }else{
                    var exist_variant = _.find(self.variant_info, function(variant_rec){
                        if(variant_rec.id === variant.id){
                            var qty = variant_rec['qty']
                            variant_rec['qty'] = qty + 1;
                        }
                        return variant_rec.id === variant.id;
                    });
                    if(!exist_variant){
                        self.variant_info.push(vals);
                    }
                }
                if(self.variant_info && self.variant_info.length > 0){
                    var contents = $('.modifiers-list-contents')
                    var line_html = QWeb.render('VariantVirtualCartLines', {
                        widget: self,
                        variant_info: self.variant_info,
                    });
                    contents.html(line_html);
                }
            }else{
                $('.modifiers-list-contents').html('');
            }
            if(self.variant_info && self.variant_info.length > 0){
                $('.proceed').css({
                    'background':'#50b6a0 none repeat scroll 0% 0%',
                    'color':'#fff',
                });
            }else{
                $('.proceed').css({
                    'background':'#000',
                    'color':'#fff',
                });
            }
            $('a.js_variant_qty').click(function(ev){
                ev.preventDefault();
                var $link = $(ev.currentTarget);
                var $input = $link.parent().parent().find("input");
                var product_elem = $('.product_content[data-line-id="'+$input.attr("name")+'"]')
                if(!product_elem.hasClass('select_item')){
                    product_elem.addClass('select_item')
                }
                var min = parseFloat($input.data("min") || 1);
                var max = parseFloat($input.data("max") || $input.val());
                var total_qty = parseFloat($input.data("total-qty") || 0);
                var quantity = ($link.has(".fa-minus").length ? -1 : 1) + parseFloat($input.val(),10);
                $input.val(quantity > min ? quantity : min);
                $input.change();
            })
        },
        replace: function($target){
            this.renderElement();
            var target = $target[0];
            target.parentNode.replaceChild(this.el,target);
        },

        set_filter: function(attribute_id, value_id){
            this.filters[attribute_id] = value_id;
                this.filter_variant();
        },

        reset_filter: function(attribute_id){
            if (attribute_id in this.filters){
                delete this.filters[attribute_id];
            }
            this.filter_variant();
        },

        filter_variant: function(){
            var self = this;
            var value_list = []
            var filter_variant_list = [];
            var found;
            for (var item in this.filters){
                value_list.push(parseInt(this.filters[item]));
            }
            for (var index in this.variant_list){
                var variant = this.variant_list[index];
                found = true;
                if(value_list.length > 1){
                    if(JSON.stringify(value_list)==JSON.stringify(variant.product_template_attribute_value_ids)){
                        filter_variant_list.push(variant);
                    }
                }else if(value_list.length == 0){
                    filter_variant_list.push(variant);
                }else{
                    for (var i = 0; i < value_list.length; i++){
                        var attribute_value_list = this.pos.db.product_template_attribute;
                        for(var j = 0; j < attribute_value_list.length; j++){
                            if(attribute_value_list[j].product_attribute_value_id[0] === value_list[i]){
                                for(var k =0;k<attribute_value_list[j].ptav_product_variant_ids.length;k++){
                                    if(attribute_value_list[j].ptav_product_variant_ids[k] == variant.id){
                                            filter_variant_list.push(variant);
                                    }
                                }
                            }
                        }
                    }
                }
            }
            this.renderElement(filter_variant_list);
        },

        set_variant_list: function(variant_list){
            this.variant_list = variant_list;
            this.filter_variant_list = variant_list;
            this.renderElement();
        },
        get_product_image_url: function(product){
            return window.location.origin + '/web/image?model=product.product&field=image_128&id='+product.id;
        },
        render_variant: function(variant){
            var order = this.pos.get_order();
            var image_url = self.get_product_image_url(variant);
            var variant_html = QWeb.render('VariantWidget', {
                    widget:  this,
                    variant: variant,
                    image_url: image_url,
                    pricelist: order.pricelist,
                });
            var variant_node = document.createElement('div');
            variant_node.innerHTML = variant_html;
            variant_node = variant_node.childNodes[1];
            return variant_node;
        },
        renderElement: function(new_filter_variant_list) {
            var self = this;
            var el_html  = QWeb.render(this.template, {widget: this});
            var el_node = document.createElement('div');
            el_node.innerHTML = el_html;
            el_node = el_node.childNodes[1];
            if(this.el && this.el.parentNode){
                this.el.parentNode.replaceChild(el_node,this.el);
            }
            this.el = el_node;
            var list_container = el_node.querySelector('.variant-list');
            if(! new_filter_variant_list){
                var filter_variant_list = this.filter_variant_list
            }else{
                var filter_variant_list = new_filter_variant_list
            }
            for(var i = 0, len = filter_variant_list.length; i < len; i++){
                var variant_node = this.render_variant(filter_variant_list[i]);
                variant_node.addEventListener('click',this.click_variant_handler);
                list_container.appendChild(variant_node);
            }
        },

    });

/* ********************************************************
Define: pos_product_template.AttributeListWidget

    - This widget will display a list of Attribute;
*********************************************************** */
    
    var AttributeListWidget = PosBaseWidget.extend({
        template:'AttributeListWidget',

        init: function(parent, options) {
            var self = this;
            this.attribute_list = [];
            this.product_template = null;
            this.click_set_attribute_handler = function(event){
                var parent = this.parentElement.parentElement.parentElement;
                if(this.children[0].classList.contains("selected")){
                    this.children[0].classList.remove('selected');
                    self.__parentedParent.variant_list_widget.reset_filter(this.dataset['attributeId']);
                }else{
                    for (var i = 0 ; i < parent.children[1].children[0].children.length; i ++){
                        var elem = parent.children[1].children[0].children[i];
                        elem.children[0].classList.remove('selected');
                    }
                    this.children[0].classList.add('selected');
                    self.__parentedParent.variant_list_widget.set_filter(this.dataset['attributeId'], this.dataset['attributeValueId']);
                }
            };
            this.click_reset_attribute_handler = function(event){
                var parent = this.parentElement;
                parent.children[0].classList.remove('selected');
                for (var i = 0 ; i < parent.children[1].children[0].children.length; i ++){
                    var elem = parent.children[1].children[0].children[i];
                    elem.children[0].classList.remove('selected');
                }
                this.classList.add('selected');
                self.__parentedParent.variant_list_widget.reset_filter(this.dataset['attributeId']);
            };
            this._super(parent, options);
        },

        replace: function($target){
            this.renderElement();
            var target = $target[0];
            target.parentNode.replaceChild(this.el,target);
        },

        set_attribute_list: function(attribute_list, product_template){
            this.attribute_list = attribute_list;
            this.product_template = product_template;
            this.renderElement();
        },

        render_attribute: function(attribute){
            var attribute_html = QWeb.render('AttributeWidget',{
                    widget:  this,
                    attribute: attribute,
                });
            var attribute_node = document.createElement('div');
            attribute_node.innerHTML = attribute_html;
            attribute_node = attribute_node.childNodes[1];

            var list_container = attribute_node.querySelector('.value-list');
            for(var i = 0, len = attribute.value_ids.length; i < len; i++){
                var value = this.pos.db.get_product_attribute_value_by_id(attribute.value_ids[i]);
                var product_list = this.pos.db.get_product_by_ids(this.product_template.product_variant_ids);
                var subproduct_list = this.pos.db.get_product_by_value_and_products(value.id, product_list);
                var variant_qty = subproduct_list.length;

                if (variant_qty != 0) {
                    var value_node = this.render_value(value, variant_qty);
                    value_node.addEventListener('click', this.click_set_attribute_handler);
                    list_container.appendChild(value_node);
                }
            };
            return attribute_node;
        },

        render_value: function(value, variant_qty){
            var value_html = QWeb.render('AttributeValueWidget',{
                    widget:  this,
                    value: value,
                    variant_qty: variant_qty,
                });
            var value_node = document.createElement('div');
            value_node.innerHTML = value_html;
            value_node = value_node.childNodes[1];
            return value_node;
        },

        renderElement: function() {
            var self = this;
            var el_html  = QWeb.render(this.template, {widget: this});
            var el_node = document.createElement('div');
            el_node.innerHTML = el_html;
            el_node = el_node.childNodes[1];
            if(this.el && this.el.parentNode){
                this.el.parentNode.replaceChild(el_node,this.el);
            }
            this.el = el_node;
            var list_container = el_node.querySelector('.attribute-list');
            for(var i = 0, len = this.attribute_list.length; i < len; i++){
                var attribute_node = this.render_attribute(this.attribute_list[i]);
                attribute_node.querySelector('.attribute-name').addEventListener('click', this.click_reset_attribute_handler);
                list_container.appendChild(attribute_node);
            };
        },

    });

    chrome.OrderSelectorWidget.include({
         start: function(){
             this._super();
             var customer_display = this.pos.config.customer_display;
             if(this.pos.get_order()){
                if(customer_display){
                    this.pos.get_order().mirror_image_data();
                }
             }
         },
        deleteorder_click_handler: function(event, $el) {
            var self  = this;
            $('.show-left-cart').hide();
            if(self.gui.get_current_screen() == "receipt"){
                return
            }
            var order = this.pos.get_order();
            var customer_display = this.pos.config.customer_display;
            if (!order) {
                return;
            } else if ( !order.is_empty() ){
                this.gui.show_popup('confirm',{
                    'title': _t('Destroy Current Order ?'),
                    'body': _t('You will lose any data associated with the current order'),
                    confirm: function(){
                        self.pos.delete_current_order();
                        $('#slidemenubtn1').css({'right':'0px'});
                        $('.product-list-container').css('width','100%');
                        $('#wrapper1').addClass('toggled');
                        // if(customer_display){
                        // 	self.pos.get_order().mirror_image_data(true);
                        // }
                    },
                });
            } else {
                this.pos.delete_current_order();
                 if(customer_display){
                    if(self.pos.get_order() && self.pos.get_order().mirror_image_data()){
                      self.pos.get_order().mirror_image_data(true);
                    }
                 }
                 $('#slidemenubtn1').css({'right':'0px'});
                 $('.product-list-container').css('width','100%');
                 $('#wrapper1').addClass('toggled');
            }
        },
        renderElement: function(){
            var self = this;
            this._super();
             var customer_display = this.pos.config.customer_display;
             this.$('.order-button.select-order').click(function(event){
                if(self.pos.get_order() && customer_display){
                    self.pos.get_order().mirror_image_data(true);
                }
             });
             this.$('.neworder-button').click(function(event){
                if(self.pos.get_order() && customer_display){
                    self.pos.get_order().mirror_image_data(true);
                }
             });
             this.$('.deleteorder-button').click(function(event){
                if(self.pos.get_order() && customer_display){
                    self.pos.get_order().mirror_image_data(true);
                }
             });
            if(this.pos.config.enable_automatic_lock && self.pos.get_cashier().access_pos_lock){
                var time_interval = this.pos.config.time_interval || 3;
                start_lock_timer(time_interval,self);
            }
            // Click on Manual Lock button
            $('.order-button.lock_button').click(function(){
                self.gui.show_popup('lock_popup');
            });
            // Click on Unlock button
            $('.unlock_button').click(function(){
                $('.freeze_screen').removeClass("active_state");
                $('.unlock_button').hide();
                $('.unlock_button').css('z-index',0);
                self.gui.show_screen('bite_login_screen');
                $('.get-input').focus();
            });
        },
    });

    return{
        VariantListWidget:VariantListWidget,
        AttributeListWidget:AttributeListWidget,
    }

});
