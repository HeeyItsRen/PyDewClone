import pygame
from settings import *
from support import *
from player import Player
from overlay import Overlay
from sprites import Generic, Interaction, Water, Tree, WildFlower, Particle
from pytmx.util_pygame import load_pygame
from transition import Transition
from soil import SoilLayer
from sky import Rain, Sky
from random import randint
from menu import Menu

class Level:
    def __init__(self):
        self.display_surface = pygame.display.get_surface() #Allows the level to draw straight on the main display to the player
        
        #Sprite groups
        self.all_sprites = CameraGroup() #Draw and update any sprites in the game
        self.collision_sprites = pygame.sprite.Group() #Keep track of collision sprites
        self.tree_sprites = pygame.sprite.Group() #Tree Groups
        self.interaction_sprites = pygame.sprite.Group() #interaetion groups
        
        self.soil_layer = SoilLayer(self.all_sprites, self.collision_sprites)
        self.setup()
        self.overlay = Overlay(self.player)
        self.transition = Transition(self.reset, self.player)
        
        #Sky
        self.rain = Rain(self.all_sprites)
        self.raining = randint(0, 10) > 7
        self.soil_layer.raining = self.raining
        self.sky = Sky()
        
        #Shop
        self.menu = Menu(self.player, self.toggle_shop)
        self.shop_active = False
        
        #Sounds
        self.success = pygame.mixer.Sound('../audio/success.wav')
        self.success.set_volume(0.1)
        
        self.bgm = pygame.mixer.Sound('../audio/music.wav')
        self.bgm.set_volume(0.05)
        self.bgm.play(loops = -1)
        
    def setup(self):
        
        tmx_data = load_pygame('../data/map.tmx')
        
        #IMPORTS
        #House
        for layer in ['HouseFloor', 'HouseFurnitureBottom']: #Housefloor before funiturebottom because it draws the floor first the the bottom
            for x, y, surface in tmx_data.get_layer_by_name(layer).tiles():
                Generic((x * TILE_SIZE, y * TILE_SIZE), surface, self.all_sprites, LAYERS['house bottom'])
        
        for layer in ['HouseWalls', 'HouseFurnitureTop']: 
            for x, y, surface in tmx_data.get_layer_by_name(layer).tiles():
                Generic((x * TILE_SIZE, y * TILE_SIZE), surface, self.all_sprites)    
                
        #Fence        
        for x, y, surface in tmx_data.get_layer_by_name('Fence').tiles():
            Generic((x * TILE_SIZE, y * TILE_SIZE), surface, [self.all_sprites, self.collision_sprites])            
                
        #Water
        water_frames = import_folder('../graphics/water')
        for x, y, surface in tmx_data.get_layer_by_name('Water').tiles():
            Water((x * TILE_SIZE, y * TILE_SIZE), water_frames, self.all_sprites)

        #Trees
        for obj in tmx_data.get_layer_by_name('Trees'):
            Tree(position = (obj.x, obj.y),
                 surface = obj.image,
                 groups = [self.all_sprites, self.collision_sprites, self.tree_sprites],
                 name = obj.name,
                 player_add = self.player_add)
            
        #WildFlowers        
        for obj in tmx_data.get_layer_by_name('Decoration'):
            WildFlower((obj.x, obj.y), obj.image, [self.all_sprites, self.collision_sprites])
              
        #Collision Tiles
        for x, y, surface in tmx_data.get_layer_by_name('Collision').tiles():
            Generic((x * TILE_SIZE, y * TILE_SIZE), pygame.Surface((TILE_SIZE, TILE_SIZE)), self.collision_sprites)
                      
        #Player
        for obj in tmx_data.get_layer_by_name('Player'):
            if obj.name == 'Start':
                self.player = Player(position = (obj.x, obj.y),
                                     group = self.all_sprites,
                                     collision_sprites = self.collision_sprites,
                                     tree_sprites = self.tree_sprites,
                                     interaction = self.interaction_sprites,
                                     soil_layer = self.soil_layer,
                                     toggle_shop = self.toggle_shop)
            
            if obj.name == 'Bed':
                Interaction(position = (obj.x, obj.y),
                            size = (obj.width, obj.height),
                            groups = self.interaction_sprites,
                            name = obj.name)    

            if obj.name == 'Trader':
                Interaction(position = (obj.x, obj.y),
                            size = (obj.width, obj.height),
                            groups = self.interaction_sprites,
                            name = obj.name) 
        
        Generic(
            position = (0, 0), 
            surface = pygame.image.load('../graphics/world/ground.png').convert_alpha(), 
            groups = self.all_sprites, 
            z = LAYERS['ground'])
        
    def player_add(self, item):
        self.success.play()
        self.player.item_inventory[item] += 1
        
    def toggle_shop(self):
        self.shop_active = not self.shop_active
        
    def reset(self):
        #Apples on the Trees
        for tree in self.tree_sprites.sprites():
            for apple in tree.apple_sprites.sprites():
                apple.kill()
            tree.create_fruit()
            
        #Plants
        self.soil_layer.update_plants()
        
        #Soils
        self.soil_layer.remove_water()
        
        self.raining = randint(0, 10) > 7
        self.soil_layer.raining = self.raining
        if self.raining:
            self.soil_layer.water_all()
        
        #Sky
        self.sky.start_color = [255, 255, 255]
        
    def plant_collision(self):
        if self.soil_layer.plant_sprites:
            for plant in self.soil_layer.plant_sprites.sprites():
                if plant.harvestable and plant.rect.colliderect(self.player.hitbox):
                    self.player_add(plant.plant_type)
                    plant.kill()
                    Particle(plant.rect.topleft, plant.image, self.all_sprites, z = LAYERS['main'])
                    self.soil_layer.grid[plant.rect.centery // TILE_SIZE][plant.rect.centerx // TILE_SIZE].remove('P')
        
    def run(self, dt):
        
        #Drawing Logic
        self.display_surface.fill('black')
        self.all_sprites.custom_draw(self.player)
        
        #Updates
        if self.shop_active:
            self.menu.update()
        else:
            self.all_sprites.update(dt) #Updates all sprites in the game E.g the player
            self.plant_collision()
        
        #Weather
        self.overlay.display()
        #Rain
        if self.raining and not self.shop_active:
            self.rain.update()
        #Daytime
        self.sky.display(dt)
        
        #Transition Overlay
        if self.player.sleep:
            self.transition.play()
            
        
class CameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.math.Vector2()
    
    def custom_draw(self, player):
        self.offset.x = player.rect.centerx - SCREEN_WIDTH / 2 #Offset is going to be by how much we will shift sprite relative to player
        self.offset.y = player.rect.centery - SCREEN_HEIGHT / 2
        
        for sprite in sorted(self.sprites(), key = lambda sprite: (sprite.z, sprite.rect.centery)):
            offset_rect = sprite.rect.copy()
            offset_rect.center -= self.offset
            self.display_surface.blit(sprite.image, offset_rect) #Mandatory image and rectangle to draw images  
        
            #Analytics to see collision
            if sprite == player:
                # pygame.draw.rect(self.display_surface, 'red', offset_rect, 5)
                # hitbox_rect = player.hitbox.copy()
                # hitbox_rect.center = offset_rect.center
                # pygame.draw.rect(self.display_surface, 'green', hitbox_rect, 5)
                target_pos = offset_rect.center + PLAYER_TOOL_OFFSET[player.status.split('_')[0]]
                pygame.draw.circle(self.display_surface, 'blue', target_pos, 5)
        
        
        