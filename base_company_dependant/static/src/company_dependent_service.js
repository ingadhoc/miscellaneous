/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Servicio centralizado para el fetching y caché del metadata
 * de campos company_dependent.
 *
 * - Al realizar la primera petición para un registro, hace UNA sola llamada
 *   RPC a ``base.company.dependant.get_company_dependent_meta`` (que a su vez
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
    }

    _key(resModel, resId) {
        return `${resModel}:${resId}`;
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
            .call("base.company.dependant", "get_company_dependent_meta", [
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
