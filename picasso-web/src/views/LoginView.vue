<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import DemoAccesos from '@/components/DemoAccesos.vue'
import Marca from '@/components/Marca.vue'
import MaterialProyecto from '@/components/MaterialProyecto.vue'
import QrCelular from '@/components/QrCelular.vue'
import { CLAVE_DEMO, DEMO } from '@/lib/demo.js'
import { HAY_MATERIAL } from '@/lib/proyecto.js'
import { mensajeError } from '@/lib/formato.js'
import { safeNext, useAuthStore } from '@/stores/auth.store.js'
import { usePerfilStore } from '@/stores/perfil.store.js'

const FOTOS = [
  { src: '/sucursales/lerma.jpg', nombre: 'Lerma' },
  { src: '/sucursales/toluca.jpg', nombre: 'Toluca' },
  { src: '/sucursales/circuito.jpg', nombre: 'Circuito' },
  { src: '/sucursales/churubusco.jpg', nombre: 'Churubusco' },
  { src: '/sucursales/periferico.jpg', nombre: 'Periférico' },
  { src: '/sucursales/vaqueritos.jpg', nombre: 'Vaqueritos' },
]

const auth = useAuthStore()
const perfil = usePerfilStore()
const router = useRouter()
const ruta = useRoute()

const correo = ref('')
const clave = ref('')
const verClave = ref(false)
const enviando = ref(false)
const error = ref('')
const actual = ref(0)
const demoCargando = ref('')
// En la demo el formulario queda plegado: lo normal es entrar con un toque.
const verFormulario = ref(!DEMO)
let reloj = null

onMounted(() => {
  reloj = setInterval(() => (actual.value = (actual.value + 1) % FOTOS.length), 5500)
})
onBeforeUnmount(() => clearInterval(reloj))

async function entrarCon(email, password) {
  error.value = ''
  try {
    const r = await auth.login({ email, password })
    if (r.status !== 'signed-in') {
      error.value = 'Esta cuenta pide un segundo factor que la app aún no maneja.'
      return
    }
    perfil.limpiar()
    await perfil.cargar(true)
    router.replace(safeNext(ruta.query.next))
  } catch (e) {
    error.value =
      e.response?.status === 401
        ? 'El correo o la contraseña no son correctos.'
        : e.response?.status === 429
          ? 'Demasiados intentos. Espera unos minutos.'
          : mensajeError(e)
  }
}

async function entrar() {
  enviando.value = true
  await entrarCon(correo.value.trim(), clave.value)
  enviando.value = false
}

async function entrarDemo(email) {
  demoCargando.value = email
  await entrarCon(email, CLAVE_DEMO)
  demoCargando.value = ''
}
</script>

<template>
  <div class="relative min-h-dvh overflow-clip bg-[#000000] text-[#f5f7fa]">
    <!-- Fotos reales de las sucursales, una tras otra -->
    <div class="absolute inset-0">
      <img
        v-for="(f, i) in FOTOS"
        :key="f.src"
        :src="f.src"
        alt=""
        class="foto-cubierta absolute inset-0 transition-opacity duration-[1600ms]"
        :class="i === actual ? 'opacity-100' : 'opacity-0'"
      />
      <div class="absolute inset-0 bg-gradient-to-b from-black/60 via-black/45 to-black" />
    </div>

    <div class="relative flex min-h-dvh flex-col" style="padding-top: env(safe-area-inset-top)">
      <div class="contenedor flex items-center justify-between pt-5">
        <span class="etiqueta !text-[#f5f7fa]/70">Seis sucursales</span>
        <span class="etiqueta !text-[#f5f7fa]/70">Picasso {{ FOTOS[actual].nombre }}</span>
      </div>

      <div class="contenedor flex flex-1 flex-col justify-end pb-8 md:flex-row md:items-end md:justify-between md:gap-16 md:pb-16">
        <div class="mt-10 mb-8 md:sticky md:bottom-10 md:mt-0 md:mb-0 md:max-w-xl">
          <Marca :alto="118" class="mb-6 md:!h-[150px]" />
          <p class="etiqueta mb-3 !text-[#f5f7fa]/70">Mantenimiento y limpieza</p>
          <h1 class="serif text-[42px] leading-[1.02] text-[#f5f7fa] md:text-[58px]">
            Revisar, documentar <em class="!text-[#fe7877]">y resolver.</em>
          </h1>
          <p class="mt-4 max-w-sm text-[15px] text-[#f5f7fa]/65">
            Inspecciones de gerente y ama de llaves, evidencia por punto y control de las seis sucursales.
          </p>
          <!-- En pantalla grande: para pasarla al celular sin teclear la dirección. -->
          <QrCelular oscuro class="mt-8 hidden w-fit md:flex" />
        </div>

        <div class="flex w-full flex-col gap-3 md:max-w-sm">
        <DemoAccesos v-if="DEMO" :cargando="demoCargando" @entrar="entrarDemo" />
        <p v-if="error && !verFormulario" class="rounded-xl bg-[#9b2335]/40 px-4 py-3 text-sm text-[#f6d5db]" role="alert">
          {{ error }}
        </p>
        <button
          v-if="!verFormulario"
          type="button"
          class="py-2 text-center text-sm font-semibold text-white/70 underline decoration-white/30 underline-offset-4"
          @click="verFormulario = true"
        >
          Entrar con correo y contraseña
        </button>
        <form
          v-if="verFormulario"
          class="w-full rounded-[16px] border border-white/10 bg-black/70 p-6 backdrop-blur-xl md:p-7"
          @submit.prevent="entrar"
        >
          <p class="etiqueta mb-5 !text-[#f5f7fa]/60">Entrar</p>
          <label class="mb-1.5 block text-sm text-[#f5f7fa]/75" for="correo">Correo</label>
          <input
            id="correo"
            v-model="correo"
            type="email"
            autocomplete="username"
            inputmode="email"
            required
            class="campo !border-white/15 !bg-white/5 !text-[#f5f7fa]"
            placeholder="nombre@picasso.mx"
          />
          <label class="mt-4 mb-1.5 block text-sm text-[#f5f7fa]/75" for="clave">Contraseña</label>
          <div class="relative">
            <input
              id="clave"
              v-model="clave"
              :type="verClave ? 'text' : 'password'"
              autocomplete="current-password"
              required
              class="campo !border-white/15 !bg-white/5 pr-20 !text-[#f5f7fa]"
            />
            <button
              type="button"
              class="etiqueta absolute top-1/2 right-4 -translate-y-1/2 !text-[#f5f7fa]/60"
              @click="verClave = !verClave"
            >
              {{ verClave ? 'Ocultar' : 'Ver' }}
            </button>
          </div>
          <p v-if="error" class="mt-4 rounded-xl bg-[#9b2335]/30 px-4 py-3 text-sm text-[#f6d5db]" role="alert">
            {{ error }}
          </p>
          <button type="submit" class="boton boton-vino mt-6 w-full" :disabled="enviando">
            {{ enviando ? 'Entrando…' : 'Entrar' }}
          </button>
          <p class="mt-4 text-center text-xs text-[#f5f7fa]/45">¿Olvidaste tu contraseña? Pídela a la administración.</p>
        </form>
        <MaterialProyecto v-if="HAY_MATERIAL" oscuro />
        </div>
      </div>
    </div>
  </div>
</template>
