"""Iluminação: modelo de Lambert por face, com luz direcional e termo ambiente."""
from __future__ import annotations

import numpy as np

from xadrez.graphics.vector import Vector3D

# Abajur alto, à esquerda e à frente do lado das brancas: a sombra cai para trás e à direita.
LAMP_DIRECTION = (0.42, -1.0, -0.30)
LAMP_COLOR = (1.0, 0.93, 0.82)
# Parte do ambiente é luz rebatida que vem de cima; o resto vale para qualquer normal.
# Sem isso, as faces do lado escuro teriam todas a mesma cor e as facetas sumiriam.
_SKY_FILL_SHARE = 0.35


class DirectionalLight:
    """Luz com a mesma direção em todo o mundo, como um abajur distante.

    `direction` é o sentido em que a luz viaja, da fonte para a cena.
    """

    def __init__(self, direction=LAMP_DIRECTION, color=LAMP_COLOR, ambient: float = 0.40, diffuse: float = 0.72):
        self.direction = np.asarray(direction, dtype=float)
        self.to_light = (-Vector3D.from_array(direction)).normalized().as_array()
        self.color = np.asarray(color, dtype=float)
        self.ambient = ambient
        self.diffuse = diffuse

    def shade(self, normals: np.ndarray, base_color) -> np.ndarray:
        """Cor de cada face, de 0 a 255, para normais unitárias (M, 3).

        Lambert: a intensidade cai com o cosseno do ângulo entre a normal e a luz, pois a
        mesma quantidade de luz se espalha por uma área maior quando a face está oblíqua.
            I = ambiente + difusa max(0, n.l)
            cor = base I cor_da_luz
        A sombra projetada é tratada à parte, em `planar_shadow`.
        """
        lambert = np.maximum(normals @ self.to_light, 0.0)
        sky = 1.0 - _SKY_FILL_SHARE + _SKY_FILL_SHARE * (normals[:, 1] + 1.0) / 2.0
        intensity = self.ambient * sky + self.diffuse * lambert
        return np.clip(np.asarray(base_color, dtype=float) * intensity[:, None] * self.color, 0.0, 255.0)
