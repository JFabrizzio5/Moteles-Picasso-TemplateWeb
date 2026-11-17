import { defineStore } from 'pinia'

import * as picasso from '@/services/picasso.js'

/** Quién usa la app (puesto y sucursal) y las sucursales, leídos una vez. */
export const usePerfilStore = defineStore('perfil', {
  state: () => ({ perfil: null, sucursales: [], cargando: null }),
  getters: {
    rol: (s) => s.perfil?.rol ?? null,
    esPersonal: (s) => ['gerente', 'ama_llaves'].includes(s.perfil?.rol),
    esGerente: (s) => s.perfil?.rol === 'gerente',
    esAma: (s) => s.perfil?.rol === 'ama_llaves',
    veTodas: (s) => ['propietario', 'admin'].includes(s.perfil?.rol),
    esAdmin: (s) => s.perfil?.rol === 'admin',
    miSucursal: (s) => s.sucursales.find((x) => x.id === s.perfil?.sucursal_id) ?? null,
  },
  actions: {
    cargar(forzar = false) {
      if (this.perfil && !forzar) return Promise.resolve(this.perfil)
      if (!this.cargando) {
        this.cargando = Promise.all([picasso.perfil(), picasso.sucursales()])
          .then(([perfil, sucursales]) => {
            this.perfil = perfil
            this.sucursales = sucursales
            return perfil
          })
          .finally(() => {
            this.cargando = null
          })
      }
      return this.cargando
    },
    sucursal(id) {
      return this.sucursales.find((x) => x.id === Number(id)) ?? null
    },
    limpiar() {
      this.$reset()
    },
  },
})
