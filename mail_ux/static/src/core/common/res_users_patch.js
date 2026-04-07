import { fields } from "@mail/core/common/record";
import { ResUsers } from "@mail/core/common/res_users_model";
import { patch } from "@web/core/utils/patch";

patch(ResUsers.prototype, {
    write_date: fields.Datetime(),
});
