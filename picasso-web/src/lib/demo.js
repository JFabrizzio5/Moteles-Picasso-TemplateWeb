// Modo demo: accesos de un toque con las cuentas de ejemplo.
// Se enciende con VITE_DEMO=si y VITE_DEMO_CLAVE en el .env del build
// (.env.movil y .env.development). Sin esas dos variables no aparece nada.

export const DEMO = import.meta.env.VITE_DEMO === 'si' && !!import.meta.env.VITE_DEMO_CLAVE
export const CLAVE_DEMO = import.meta.env.VITE_DEMO_CLAVE ?? ''

export const SUCURSALES_DEMO = [
  { clave: 'ler', nombre: 'Lerma', gerente: 'Laura Méndez', ama: 'Rosa Hernández' },
  { clave: 'tol', nombre: 'Toluca', gerente: 'Jorge Salinas', ama: 'María Torres' },
  { clave: 'cir', nombre: 'Circuito', gerente: 'Andrea Ruiz', ama: 'Guadalupe Díaz' },
  { clave: 'chu', nombre: 'Churubusco', gerente: 'Ricardo Peña', ama: 'Alicia Romero' },
  { clave: 'per', nombre: 'Periférico', gerente: 'Sofía Lozano', ama: 'Carmen Vega' },
  { clave: 'vaq', nombre: 'Vaqueritos', gerente: 'Héctor Campos', ama: 'Isabel Flores' },
]
