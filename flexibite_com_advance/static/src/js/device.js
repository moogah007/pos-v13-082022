odoo.define('flexibite_com_advance.devices', function (require) {
    "use strict";

    var BarcodeReader = require('point_of_sale.BarcodeReader');

    BarcodeReader.include({
        scan: function(code){
            var self = this;
            var current_screen = self.pos.gui.get_current_screen();
            if(current_screen == 'bite_login_screen'){
                var user = _.find(this.pos.users, function(obj) { return obj.rfid_no == code });
                if(user){
                    self.pos.chrome.screens.bite_login_screen.login_user(user.login, user.pos_security_pin);
                }else{
                    var img = "<img src='/flexibite_com_advance/static/src/img/scan_rfid_red.png' style='height:285px;width:auto;'/>"
                    $("#image").html(img)
                    setTimeout(function(){
                        var img = "<img src='/flexibite_com_advance/static/src/img/scan_rfid.png' style='height:285px;width:auto;'/>"
                        $("#image").html(img)
                    }, 1000);
                }
            } else {
                this._super(code);
            }
        },
    });

});
