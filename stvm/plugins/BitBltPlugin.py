from ..spurobjects import ImmediateInteger as integer
from ..utils import *
from ..primitives import PrimitiveFail



def primitiveCopyBits(self, context, vm):
    print("Buggy implementation of copybits")
    try:
        dst = self[0][0]
        src = self[1][0]
        destX = self[4].value
        destY = self[5].value
        width = self[6].value
        height = self[7].value

        import pygame
        screen = vm.screen
        surface = pygame.Surface((width, height))
        pixelArray = pygame.PixelArray(surface)

        for y in range(height):
            for x in range(width):
                pixelArray[x, y] = src[y * height + x].value

        del pixelArray
        screen.blit(surface, (destX, destY))
        pygame.display.flip()
    except Exception:
        ...


def primitiveDisplayString(component, string, start, stop, glyphMap, xTable, kern, context, vm):
    import pygame
    destX = component[6].value
    screen = vm.screen
    font = pygame.font.Font(None, 20)
    text = font.render(string.as_text()[start.value-1:stop.value], True, (255, 0, 0))
    screen.blit(text, (destX, 20))
    pygame.display.flip()
