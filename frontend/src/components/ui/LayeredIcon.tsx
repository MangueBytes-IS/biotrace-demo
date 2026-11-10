import type { CSSProperties } from 'react'

export interface IconLayer {
  src: string
  /** Posição da camada dentro do ícone (CSS inset, como no Figma) */
  box: string
  /** Expansão para o traço (CSS inset negativo, como no Figma) */
  bleed: string
}

/** Ícones exportados do Figma em várias camadas vetoriais sobrepostas */
export default function LayeredIcon({ width, height, layers, style }: {
  width: number
  height: number
  layers: IconLayer[]
  style?: CSSProperties
}) {
  return (
    <span className="layered-icon" style={{ width, height, ...style }} aria-hidden="true">
      {layers.map((layer) => (
        <span key={layer.src + layer.box} className="layered-icon__box" style={{ inset: layer.box }}>
          <span className="layered-icon__bleed" style={{ inset: layer.bleed }}>
            <img alt="" src={layer.src} />
          </span>
        </span>
      ))}
    </span>
  )
}
