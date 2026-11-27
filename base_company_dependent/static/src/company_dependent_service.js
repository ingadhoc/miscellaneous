/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Servicio centralizado para el fetching y caché del metadata
 * de campos company_dependent.
 *
 * - Al realizar la primera petición para un registro, hace UNA sola llamada
 *   RPC a ``base.company.dependent.get_company_dependent_meta`` (que a su vez
 *   ejecuta una única query SQL para todos los campos company_dependent
 *   del modelo).
 * - Las llamadas concurrentes al mismo registro comparten la misma Promise.
 * - El resultado se cachea hasta que se llame a ``invalidate()``.
 */
class CompanyDependentService {
    constructor(env, { orm }) {
        this.orm = orm;
        /**
         * Mapa de cacheKey → Promise<meta> o meta (objeto plano una vez resuelto).
         * @type {Map<string, Promise<Object>|Object>}
         */
        this._cache = new Map();
        /**
         * Tandas en vuelo de resolveManageableFields, por cacheKey.
         * @type {Map<string, {names: Set<string>, promise: Promise}>}
         */
        this._batches = new Map();
    }

    _key(resModel, resId) {
        return `${resModel}:${resId}`;
    }

    /**
     * Devuelve qué campos de ``candidates`` puede gestionar el diálogo.
     *
     * Una pantalla de Ajustes tiene decenas de bloques y cada uno pregunta por
     * los suyos: las preguntas del mismo tick se juntan en UNA llamada con la
     * unión de los nombres, y cada bloque filtra después los propios. Así la
     * pantalla paga una consulta, no una por bloque.
     *
     * @returns {Promise<Array<{field_name: string, field_string: string}>>}
     *          los gestionables de toda la tanda, no solo los de quien pregunta.
     */
    resolveManageableFields(resModel, resId, candidates) {
        const key = this._key(resModel, resId);
        if (!this._batches.has(key)) {
            const batch = { names: new Set(), promise: null };
            // El microtask corre cuando terminaron de montarse los bloques de
            // esta tanda, así que para entonces `names` ya los tiene a todos.
            batch.promise = Promise.resolve().then(() => {
                this._batches.delete(key);
                return this.orm.call("base.company.dependent", "resolve_manageable_fields", [
                    resModel,
                    resId,
                    [...batch.names],
                ]);
            });
            this._batches.set(key, batch);
        }
        const batch = this._batches.get(key);
        for (const name of candidates || []) {
            batch.names.add(name);
        }
        return batch.promise;
    }

    /**
     * Invalida la caché para un registro (llamar después de guardar desde el dialog).
     */
    invalidate(resModel, resId) {
        this._cache.delete(this._key(resModel, resId));
    }

    /**
     * Devuelve ``{fieldName: is_specific, ...}`` para todos los campos
     * company_dependent del modelo.  El resultado se obtiene de caché si
     * ya se cargó previamente.
     *
     * @param {string} resModel
     * @param {number} resId
     * @returns {Promise<Object>}
     */
    async getMetaForRecord(resModel, resId) {
        if (!resId) return {};
        const key = this._key(resModel, resId);
        if (this._cache.has(key)) {
            // Puede ser la Promise en vuelo o el objeto ya resuelto.
            return this._cache.get(key);
        }
        const promise = this.orm
            .call("base.company.dependent", "get_company_dependent_meta", [
                resModel,
                resId,
            ])
            .then((result) => {
                // Reemplaza la Promise con el valor resuelto.
                this._cache.set(key, result);
                return result;
            })
            .catch((e) => {
                this._cache.delete(key);
                throw e;
            });
        this._cache.set(key, promise);
        return promise;
    }

    /**
     * Versión síncrona: devuelve el meta SOLO si ya está resuelto en caché,
     * o ``undefined`` si aún está pendiente.
     *
     * @param {string} resModel
     * @param {number} resId
     * @returns {Object|undefined}
     */
    getMetaSync(resModel, resId) {
        const cached = this._cache.get(this._key(resModel, resId));
        if (cached && typeof cached.then !== "function") {
            return cached;
        }
        return undefined;
    }
}

export const companyDependentService = {
    dependencies: ["orm"],
    start(env, deps) {
        return new CompanyDependentService(env, deps);
    },
};

registry.category("services").add("company_dependent", companyDependentService);
