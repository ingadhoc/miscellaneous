import { after, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { registry } from "@web/core/registry";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { addButtonToFieldSubclasses } from "@base_company_dependent/fields_patch";

class Partner extends models.Model {
    name = fields.Char();
    cd_char = fields.Char({ string: "CD Char", company_dependent: true });
    cd_integer = fields.Integer({ company_dependent: true });
    cd_float = fields.Float({ company_dependent: true });
    cd_monetary = fields.Monetary({ currency_field: "currency_id", company_dependent: true });
    cd_boolean = fields.Boolean({ company_dependent: true });
    cd_datetime = fields.Datetime({ company_dependent: true });
    cd_selection = fields.Selection({
        selection: [
            ["a", "A"],
            ["b", "B"],
        ],
        company_dependent: true,
    });
    cd_product_id = fields.Many2one({ relation: "product", company_dependent: true });
    currency_id = fields.Many2one({ relation: "res.currency" });

    _records = [
        { id: 1, name: "first", cd_char: "fallback", currency_id: 1 },
        { id: 2, name: "second", cd_char: "own", currency_id: 1 },
    ];
}

class Product extends models.Model {
    name = fields.Char();

    _records = [{ id: 37, name: "xphone" }];
}

class Currency extends models.Model {
    _name = "res.currency";

    name = fields.Char();
    symbol = fields.Char();
    position = fields.Selection({
        selection: [
            ["after", "A"],
            ["before", "B"],
        ],
    });

    _records = [{ id: 1, name: "USD", symbol: "$", position: "before" }];
}

defineModels([Partner, Product, Currency]);

const CD_FIELDS = [
    "cd_char",
    "cd_integer",
    "cd_float",
    "cd_monetary",
    "cd_boolean",
    "cd_datetime",
    "cd_selection",
    "cd_product_id",
];

function mockMeta(isSpecific = false) {
    onRpc("base.company.dependent", "get_company_dependent_meta", ({ args }) => {
        expect.step(`meta ${args[0]} ${args[1]}`);
        const resId = args[1];
        const specific = typeof isSpecific === "function" ? isSpecific(resId) : isSpecific;
        return Object.fromEntries(CD_FIELDS.map((name) => [name, specific]));
    });
}

function mockValues(fieldType = "char", extra = {}) {
    onRpc("base.company.dependent", "get_company_dependent_values", ({ args }) => {
        expect.step(`values ${args[2]}`);
        return {
            values: [
                {
                    company_id: 1,
                    company_name: "Parent Co",
                    parent_id: null,
                    level: 1,
                    has_children: true,
                    is_specific: false,
                    value_id: "fallback",
                    display_value: "fallback",
                    fallback_value_id: "fallback",
                    fallback_display_value: "fallback",
                },
                {
                    company_id: 2,
                    company_name: "Child Co",
                    parent_id: 1,
                    level: 2,
                    has_children: false,
                    is_specific: false,
                    value_id: "fallback",
                    display_value: "fallback",
                    fallback_value_id: "fallback",
                    fallback_display_value: "fallback",
                },
            ],
            field_type: fieldType,
            comodel_name: null,
            selection_options: [],
            ...extra,
        };
    });
}

test.tags("desktop");
test("button is added to every patched field type", async () => {
    mockMeta(false);
    await mountView({
        resModel: "partner",
        resId: 1,
        type: "form",
        arch: `
            <form>
                <field name="name"/>
                ${CD_FIELDS.map((name) => `<field name="${name}"/>`).join("")}
                <field name="currency_id" invisible="1"/>
            </form>`,
    });
    for (const name of CD_FIELDS) {
        expect(`.o_field_widget[name=${name}] .o_cd_btn`).toHaveCount(1, { message: name });
        expect(`.o_field_widget[name=${name}] .o_cd_wrapper`).toHaveClass("o_cd_fallback", {
            message: name,
        });
    }
    expect(".o_field_widget[name=name] .o_cd_btn").toHaveCount(0);
    expect(".o_cd_btn i.text-muted").toHaveCount(CD_FIELDS.length);
    // A single RPC serves every company_dependent field of the record.
    expect.verifySteps(["meta partner 1"]);
});

test.tags("desktop");
test("specific value is not shown as fallback", async () => {
    mockMeta(true);
    await mountView({
        resModel: "partner",
        resId: 2,
        type: "form",
        arch: `<form><field name="cd_char"/></form>`,
    });
    expect(".o_field_widget[name=cd_char] .o_cd_wrapper").not.toHaveClass("o_cd_fallback");
    expect(".o_cd_btn i").toHaveClass("text-primary");
});

test.tags("desktop");
test("editing a company_dependent char field saves the value", async () => {
    mockMeta(false);
    onRpc("partner", "web_save", ({ args }) => {
        expect.step(`web_save ${args[1].cd_char}`);
    });
    await mountView({
        resModel: "partner",
        resId: 1,
        type: "form",
        arch: `<form><field name="cd_char"/></form>`,
    });
    await contains(".o_field_widget[name=cd_char] input").edit("BC-1");
    await contains(".o_form_button_save").click();
    expect.verifySteps(["meta partner 1", "web_save BC-1"]);
});

test.tags("desktop");
test("boolean_toggle widget shows the button", async () => {
    mockMeta(false);
    await mountView({
        resModel: "partner",
        resId: 1,
        type: "form",
        arch: `<form><field name="cd_boolean" widget="boolean_toggle"/></form>`,
    });
    expect(".o_field_widget[name=cd_boolean] .o_boolean_toggle").toHaveCount(1);
    expect(".o_field_widget[name=cd_boolean] .o_cd_btn").toHaveCount(1);
});

test.tags("desktop");
test("list view shows one button per row", async () => {
    mockMeta((resId) => resId === 2);
    await mountView({
        resModel: "partner",
        type: "list",
        arch: `<list><field name="name"/><field name="cd_boolean" widget="boolean_toggle"/></list>`,
    });
    expect(".o_data_row .o_cd_btn").toHaveCount(2);
    expect(".o_data_row:eq(0) .o_cd_btn i").toHaveClass("text-muted");
    expect(".o_data_row:eq(1) .o_cd_btn i").toHaveClass("text-primary");
});

test.tags("desktop");
test("dialog saves the edited company value", async () => {
    mockMeta(false);
    mockValues("char");
    onRpc("base.company.dependent", "set_company_dependent_values", ({ args }) => {
        expect.step(`set ${JSON.stringify(args[3])}`);
        return { saved: [2], skipped: [] };
    });
    await mountView({
        resModel: "partner",
        resId: 1,
        type: "form",
        arch: `<form><field name="cd_char"/></form>`,
    });
    await contains(".o_cd_btn").click();
    expect(".o_dialog .o_cd_row").toHaveCount(2);
    expect(".o_dialog .o_cd_row_default").toHaveCount(2);
    expect(".o_dialog .o_cd_copy_btn").toHaveCount(1);

    await contains(".o_dialog .o_cd_row:eq(1) input").edit("child value");
    expect(".o_dialog .o_cd_row:eq(1)").toHaveClass("o_cd_row_specific");

    await contains(".o_dialog .btn-primary").click();
    expect(".o_dialog").toHaveCount(0);
    expect(".o_notification_content").toHaveText("Values saved successfully.");
    expect.verifySteps([
        "meta partner 1",
        "values cd_char",
        'set {"2":"child value"}',
        // the button reloads the record and the field reloads its meta
        "meta partner 1",
    ]);
});

test.tags("desktop");
test("dialog copies a parent value to its children and resets a row", async () => {
    mockMeta(false);
    mockValues("char");
    onRpc("base.company.dependent", "set_company_dependent_values", ({ args }) => {
        expect.step(`set ${JSON.stringify(args[3])}`);
        return { saved: [1, 2], skipped: [] };
    });
    await mountView({
        resModel: "partner",
        resId: 1,
        type: "form",
        arch: `<form><field name="cd_char"/></form>`,
    });
    await contains(".o_cd_btn").click();
    await contains(".o_dialog .o_cd_row:eq(0) input").edit("parent value");
    await contains(".o_dialog .o_cd_copy_btn").click();
    expect(".o_dialog .o_cd_row:eq(1) input").toHaveValue("parent value");

    await contains(".o_dialog .o_cd_row:eq(1) .btn-outline-danger").click();
    expect(".o_dialog .o_cd_row:eq(1)").toHaveClass("o_cd_row_default");

    await contains(".o_dialog .btn-primary").click();
    expect.verifySteps([
        "meta partner 1",
        "values cd_char",
        'set {"1":"parent value","2":"RESET"}',
        "meta partner 1",
    ]);
});

test.tags("desktop");
test("dialog keeps open and warns when some companies are skipped", async () => {
    mockMeta(false);
    mockValues("char");
    onRpc("base.company.dependent", "set_company_dependent_values", () => ({
        saved: [1],
        skipped: [{ id: 2, name: "Child Co", reason: "cross company" }],
    }));
    await mountView({
        resModel: "partner",
        resId: 1,
        type: "form",
        arch: `<form><field name="cd_char"/></form>`,
    });
    await contains(".o_cd_btn").click();
    await contains(".o_dialog .o_cd_row:eq(1) input").edit("x");
    await contains(".o_dialog .btn-primary").click();
    expect(".o_dialog").toHaveCount(1);
    expect(".o_notification_content").toHaveText(
        "Saved 1 company value(s). Could not save 1 due to company inconsistencies: Child Co."
    );
});

test.tags("desktop");
test("subclass that copied components before the patch still renders", async () => {
    // Simulates a widget evaluated before fields_patch.js (e.g. Many2OneBankField).
    const { CompanyDependentButton, ...staleComponents } = Many2OneField.components;
    expect(CompanyDependentButton).not.toBe(undefined);
    class EarlyMany2OneField extends Many2OneField {
        static components = staleComponents;
    }
    registry
        .category("fields")
        .add("early_many2one", buildM2OFieldDescription(EarlyMany2OneField));
    after(() => registry.category("fields").remove("early_many2one"));
    addButtonToFieldSubclasses();
    expect(EarlyMany2OneField.components.CompanyDependentButton).toBe(CompanyDependentButton);

    mockMeta(false);
    await mountView({
        resModel: "partner",
        resId: 1,
        type: "form",
        arch: `<form><field name="cd_product_id" widget="early_many2one"/></form>`,
    });
    await animationFrame();
    expect(".o_field_widget[name=cd_product_id] .o_cd_btn").toHaveCount(1);
});
