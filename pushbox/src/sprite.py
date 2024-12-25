import pygame
import const

class Sprite(pygame.sprite.Sprite):
    def __init__(self, imgPath, rowIdx, colIdx, relativePos):
        super(Sprite, self).__init__()
        self.image = pygame.image.load(imgPath)
        # ��ͼƬ��С��Ϊ wxh
        self.image = pygame.transform.scale(self.image, (const.SPRITE_SIZE_W, const.SPRITE_SIZE_H))
        self.rect = self.image.get_rect()
        self.relativePos = relativePos
        self.updateRowIdx(rowIdx)
        self.updateColIdx(colIdx)
    
    def updateRowIdx(self, rowIdx):
        self.rowIdx = rowIdx
        self.rect.y = self.relativePos[0] + rowIdx * self.rect.height

    def updateColIdx(self, colIdx):
        self.colIdx = colIdx
        self.rect.x = self.relativePos[1] + colIdx * self.rect.width
    
    def updateIdx(self, rowIdx, colIdx):
        self.updateRowIdx(rowIdx)
        self.updateColIdx(colIdx)
    
    # ʵ��һ��ͼƬ����Ⱦ����
    def draw(self, surface):
        surface.blit(self.image, self.rect)

        