from browser import document, html, timer, ajax, window
from random import random
import time

canvas = document["gameCanvas"]
ctx = canvas.getContext("2d")
WIDTH, HEIGHT = 800, 400

# --- 圖片處理：確保載入完成 ---
bird_img = html.IMG(src="/static/images/bird.png")
pig_img = html.IMG(src="/static/images/pig.png")

# 遊戲常數 - 改成20發鳥
SLING_X, SLING_Y = 120, 300
MAX_SHOTS = 20  # 改成20發

# 遊戲狀態
shots_fired = 0
total_score = 0
mouse_down = False
mouse_pos = (SLING_X, SLING_Y)
projectile = None
sent = False
game_phase = "playing"
game_over_countdown = 0

# ------------------------------------------
# 類別
# ------------------------------------------
class Pig:
    def __init__(self, x, y, size_factor=1.0):
        self.x, self.y = x, y
        # 隨機大小，最大不超過原本的1.5倍
        base_size = 40
        self.size_factor = min(1.5, max(0.8, size_factor))  # 限制在0.8到1.5倍之間
        self.w, self.h = int(base_size * self.size_factor), int(base_size * self.size_factor)
        self.alive = True
        # 根據大小調整房子的尺寸
        house_width = 120 * self.size_factor
        house_height = 50 * self.size_factor
        roof_thickness = 15 * self.size_factor
        wall_thickness = 15 * self.size_factor
        
        self.house_blocks = [
            (0, self.h, house_width, roof_thickness),  # 底部屋頂
            (0, -roof_thickness, wall_thickness, house_height),  # 左牆
            (house_width - wall_thickness, -roof_thickness, wall_thickness, house_height),  # 右牆
            (0, -roof_thickness * 2, house_width, roof_thickness)  # 頂部屋頂
        ]
        self.last_hit_time = time.time()  # 記錄最後一次被擊中的時間
        self.idle_timer = 0  # 閒置計時器
        self.move_timer = 0  # 移動計時器
        self.move_speed_x = (random() - 0.5) * 1.5  # 初始隨機移動速度
        self.move_speed_y = (random() - 0.5) * 1.5

    def draw(self):
        if self.alive:
            # 只繪製豬的圖片，隱藏房子
            if pig_img.complete:
                # 根據大小調整圖片尺寸
                ctx.drawImage(pig_img, self.x, self.y, self.w, self.h)

    def hit(self, px, py):
        return self.alive and self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

    def check_collision(self, other_pig):
        """檢查與另一隻豬是否重疊"""
        return (self.x < other_pig.x + other_pig.w and 
                self.x + self.w > other_pig.x and
                self.y < other_pig.y + other_pig.h and
                self.y + self.h > other_pig.y)

    def relocate(self, other_pigs):
        """重新定位豬的位置，確保不會與其他豬重疊"""
        MAX_ATTEMPTS = 100
        MIN_X, MAX_X = 450, WIDTH - self.w - 120
        MIN_Y, MAX_Y = 200, HEIGHT - self.h - 15
        
        for attempt in range(MAX_ATTEMPTS):
            # 嘗試隨機位置
            new_x = MIN_X + random() * (MAX_X - MIN_X)
            new_y = MIN_Y + random() * (MAX_Y - MIN_Y)
            
            # 臨時設定位置以檢查碰撞
            old_x, old_y = self.x, self.y
            self.x, self.y = new_x, new_y
            
            # 檢查是否與其他豬重疊
            collision = False
            for pig in other_pigs:
                if pig is not self and pig.alive and self.check_collision(pig):
                    collision = True
                    break
            
            # 如果沒有碰撞，保持新位置
            if not collision:
                self.last_hit_time = time.time()  # 重置計時器
                # 重新設定隨機移動速度
                self.move_speed_x = (random() - 0.5) * 1.5
                self.move_speed_y = (random() - 0.5) * 1.5
                return True
            
            # 如果有碰撞，恢復原位置
            self.x, self.y = old_x, old_y
        
        # 如果找不到合適位置，嘗試網格佈局
        return self.find_grid_position(other_pigs, MIN_X, MAX_X, MIN_Y, MAX_Y)

    def find_grid_position(self, other_pigs, min_x, max_x, min_y, max_y):
        """在網格中尋找可用位置"""
        grid_size = 60  # 網格大小
        
        # 計算可用的網格單元
        cols = int((max_x - min_x) / grid_size)
        rows = int((max_y - min_y) / grid_size)
        
        # 嘗試所有網格位置
        for r in range(rows):
            for c in range(cols):
                new_x = min_x + c * grid_size
                new_y = min_y + r * grid_size
                
                # 臨時設定位置以檢查碰撞
                old_x, old_y = self.x, self.y
                self.x, self.y = new_x, new_y
                
                # 檢查是否與其他豬重疊
                collision = False
                for pig in other_pigs:
                    if pig is not self and pig.alive and self.check_collision(pig):
                        collision = True
                        break
                
                # 如果沒有碰撞，保持新位置
                if not collision:
                    self.last_hit_time = time.time()  # 重置計時器
                    # 重新設定隨機移動速度
                    self.move_speed_x = (random() - 0.5) * 1.5
                    self.move_speed_y = (random() - 0.5) * 1.5
                    return True
                
                # 如果有碰撞，恢復原位置
                self.x, self.y = old_x, old_y
        
        # 如果還是找不到位置，放在一個默認位置
        self.x = min_x + random() * (max_x - min_x)
        self.y = min_y + random() * (max_y - min_y)
        self.last_hit_time = time.time()
        # 重新設定隨機移動速度
        self.move_speed_x = (random() - 0.5) * 1.5
        self.move_speed_y = (random() - 0.5) * 1.5
        return False

    def update(self, other_pigs):
        if not self.alive:
            return
            
        # 增加移動計時器
        self.move_timer += 1
        
        # 豬一開始就隨機移動，不需要等待30秒
        # 每30幀改變一次移動方向
        if self.move_timer > 30:
            # 隨機改變移動方向
            self.move_speed_x += (random() - 0.5) * 0.5
            self.move_speed_y += (random() - 0.5) * 0.5
            
            # 限制最大速度
            max_speed = 2.0
            self.move_speed_x = max(-max_speed, min(max_speed, self.move_speed_x))
            self.move_speed_y = max(-max_speed, min(max_speed, self.move_speed_y))
            
            self.move_timer = 0
        
        # 更新位置
        old_x, old_y = self.x, self.y
        self.x += self.move_speed_x
        self.y += self.move_speed_y
        
        # 邊界檢查
        MIN_X, MAX_X = 450, WIDTH - self.w - 120
        MIN_Y, MAX_Y = 200, HEIGHT - self.h - 15
        
        # 如果碰到邊界，反彈
        if self.x < MIN_X or self.x > MAX_X:
            self.move_speed_x = -self.move_speed_x * 0.8  # 反彈並減速
            self.x = max(MIN_X, min(MAX_X, self.x))
        
        if self.y < MIN_Y or self.y > MAX_Y:
            self.move_speed_y = -self.move_speed_y * 0.8  # 反彈並減速
            self.y = max(MIN_Y, min(MAX_Y, self.y))
        
        # 檢查是否與其他豬碰撞
        collision = False
        collision_pig = None
        for pig in other_pigs:
            if pig is not self and pig.alive and self.check_collision(pig):
                collision = True
                collision_pig = pig
                break
        
        # 如果發生碰撞，反彈並稍微分開
        if collision:
            # 恢復到碰撞前的位置
            self.x, self.y = old_x, old_y
            
            # 計算反彈方向
            dx = self.x - collision_pig.x
            dy = self.y - collision_pig.y
            
            # 避免除以零
            distance = max(0.1, (dx**2 + dy**2)**0.5)
            
            # 標準化方向向量
            dx /= distance
            dy /= distance
            
            # 反彈
            self.move_speed_x = dx * 1.5
            self.move_speed_y = dy * 1.5
            
            # 稍微分開
            self.x += dx * 5
            self.y += dy * 5
            
            # 確保不超出邊界
            self.x = max(MIN_X, min(MAX_X, self.x))
            self.y = max(MIN_Y, min(MAX_Y, self.y))
        
        # 原有的閒置計時器邏輯（現在主要用於隨機移動）
        self.idle_timer += 1
        if self.idle_timer > 60:  # 每60幀檢查一次
            # 有10%的機率改變移動方向
            if random() < 0.1:
                self.move_speed_x = (random() - 0.5) * 2.0
                self.move_speed_y = (random() - 0.5) * 2.0
            
            self.idle_timer = 0

class Bird:
    def __init__(self, x, y, vx, vy):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.w, self.h = 35, 35
        self.active = True

    def update(self):
        global total_score
        if not self.active: return
        self.vy += 0.35
        self.x += self.vx
        self.y += self.vy
        if self.y > HEIGHT - self.h or self.x > WIDTH or self.x < 0:
            self.active = False
        for p in pigs:
            if p.hit(self.x + self.w / 2, self.y + self.h / 2):
                p.relocate(pigs)
                total_score += int(50 * p.size_factor)  # 根據大小給分
                document["score_display"].text = str(total_score)
                self.active = False
                break

    def draw(self):
        if bird_img.complete:
            ctx.drawImage(bird_img, self.x, self.y, self.w, self.h)

# ------------------------------------------
# 遊戲邏輯與輸入處理
# ------------------------------------------
pigs = []

def init_level():
    global pigs
    # 建立6隻豬，每隻大小不同（最大不超過原本的1.5倍）
    pigs = []
    
    # 預設的位置（這些是原先豬會出現的位置）
    original_positions = [
        (500, 250),  # 右上角
        (600, 300),  # 右中
        (700, 200),  # 右下角
        (550, 200),  # 右上方
        (650, 250),  # 右中偏上
        (500, 300)   # 右中偏下
    ]
    
    # 調整位置確保不會重疊
    for i in range(6):
        # 創建不同大小的豬，從0.8倍到1.5倍
        size_factor = 0.8 + (i / 5) * 0.7  # 均勻分布從0.8到1.5
        pig = Pig(original_positions[i][0], original_positions[i][1], size_factor)
        pigs.append(pig)
    
    # 檢查並調整重疊的豬
    adjust_pig_positions()

def adjust_pig_positions():
    """調整豬的位置，確保它們不會重疊"""
    MAX_ATTEMPTS = 100
    MIN_X, MAX_X = 450, WIDTH - 40 - 120  # 考慮豬的最大寬度
    MIN_Y, MAX_Y = 200, HEIGHT - 40 - 15  # 考慮豬的最大高度
    
    for i in range(len(pigs)):
        pig = pigs[i]
        
        # 檢查與其他豬的碰撞
        for attempt in range(MAX_ATTEMPTS):
            collision = False
            for j in range(len(pigs)):
                if i != j and pigs[j].alive and pig.check_collision(pigs[j]):
                    collision = True
                    break
            
            # 如果沒有碰撞，繼續檢查下一隻豬
            if not collision:
                break
            
            # 如果有碰撞，移動這隻豬到新位置
            # 計算新位置（在原位置的基礎上稍微偏移）
            offset_x = (random() - 0.5) * 100
            offset_y = (random() - 0.5) * 80
            pig.x = max(MIN_X, min(MAX_X, pig.x + offset_x))
            pig.y = max(MIN_Y, min(MAX_Y, pig.y + offset_y))
        
        # 如果還是碰撞，使用網格佈局
        if collision:
            # 使用網格佈局重新定位
            cols = 3  # 3列
            rows = 2  # 2行
            grid_width = (MAX_X - MIN_X) / cols
            grid_height = (MAX_Y - MIN_Y) / rows
            
            row = i // cols
            col = i % cols
            
            pig.x = MIN_X + col * grid_width + grid_width / 2 - pig.w / 2
            pig.y = MIN_Y + row * grid_height + grid_height / 2 - pig.h / 2

def start_new_game():
    global shots_fired, total_score, projectile, sent, game_phase, game_over_countdown
    total_score, shots_fired = 0, 0
    document["score_display"].text = "0"
    projectile, sent = None, False
    game_phase = "playing"
    game_over_countdown = 0
    init_level()
    update_shots_remaining()

def update_shots_remaining():
    document["shots_remaining"].text = str(MAX_SHOTS - shots_fired)

def get_pos(evt):
    # 重要：處理手機縮放後的精確座標
    rect = canvas.getBoundingClientRect()
    # 計算畫布與實際 CSS 顯示尺寸的比例
    scale_x = canvas.width / rect.width
    scale_y = canvas.height / rect.height
    
    if hasattr(evt, "touches") and len(evt.touches) > 0:
        client_x, client_y = evt.touches[0].clientX, evt.touches[0].clientY
    elif hasattr(evt, "changedTouches") and len(evt.changedTouches) > 0:
        client_x, client_y = evt.changedTouches[0].clientX, evt.changedTouches[0].clientY
    else:
        client_x, client_y = evt.clientX, evt.clientY
        
    return (client_x - rect.left) * scale_x, (client_y - rect.top) * scale_y

def mousedown(evt):
    global mouse_down, mouse_pos
    evt.preventDefault()
    if game_phase == "playing" and projectile is None and shots_fired < MAX_SHOTS:
        mouse_down = True
        mouse_pos = get_pos(evt)

def mousemove(evt):
    global mouse_pos
    evt.preventDefault()
    if mouse_down:
        mouse_pos = get_pos(evt)

def mouseup(evt):
    global mouse_down, projectile, shots_fired
    evt.preventDefault()
    if mouse_down:
        mouse_down = False
        end_pos = get_pos(evt)
        dx, dy = SLING_X - end_pos[0], SLING_Y - end_pos[1]
        projectile = Bird(SLING_X, SLING_Y, dx * 0.25, dy * 0.25)
        shots_fired += 1
        update_shots_remaining()

# 綁定事件
canvas.bind("mousedown", mousedown)
window.bind("mousemove", mousemove) # 在視窗監聽確保拖出邊界也能運作
window.bind("mouseup", mouseup)
canvas.bind("touchstart", mousedown)
canvas.bind("touchmove", mousemove)
canvas.bind("touchend", mouseup)

# ------------------------------------------
# 繪圖與主迴圈
# ------------------------------------------
def draw_sling():
    if game_phase != "playing": return
    ctx.strokeStyle, ctx.lineWidth = "black", 4
    if mouse_down:
        mx, my = mouse_pos
        for offset in [-5, 5]:
            ctx.beginPath()
            ctx.moveTo(SLING_X + offset, SLING_Y)
            ctx.lineTo(mx, my)
            ctx.stroke()
        if bird_img.complete:
            ctx.drawImage(bird_img, mx - 17, my - 17, 35, 35)
    elif projectile is None and shots_fired < MAX_SHOTS:
        if bird_img.complete:
            ctx.drawImage(bird_img, SLING_X - 17, SLING_Y - 17, 35, 35)

def draw_score_and_shots():
    """在畫布上繪製分數和剩餘射擊次數"""
    # 繪製分數
    ctx.fillStyle = "white"
    ctx.font = "bold 24px Arial"
    ctx.textAlign = "left"
    ctx.fillText(f"分数：{total_score}", 20, 40)
    
    # 繪製剩餘射擊次數
    ctx.fillStyle = "white"
    ctx.font = "bold 24px Arial"
    ctx.fillText(f"剩余射击次数：{MAX_SHOTS - shots_fired}", 20, 80)

def send_score():
    global sent
    if sent: return
    sent = True
    req = ajax.ajax()
    req.open("POST", "/submit_score", True)
    req.set_header("Content-Type", "application/json")
    req.send(window.JSON.stringify({"score": total_score}))

def loop():
    global projectile, game_phase, game_over_countdown
    ctx.clearRect(0, 0, WIDTH, HEIGHT)
    
    # 繪製遊戲背景
    ctx.fillStyle = "#87CEEB"  # 天空藍
    ctx.fillRect(0, 0, WIDTH, HEIGHT * 0.7)
    
    ctx.fillStyle = "#8B4513"  # 土地棕
    ctx.fillRect(0, HEIGHT * 0.7, WIDTH, HEIGHT * 0.3)
    
    # 繪製彈弓架
    ctx.fillStyle = "#8B4513"
    ctx.fillRect(SLING_X - 15, SLING_Y - 40, 30, 60)
    ctx.fillRect(SLING_X - 30, SLING_Y, 60, 10)
    
    # 繪製分數和剩餘射擊次數
    draw_score_and_shots()
    
    # 更新每隻豬的狀態
    for p in pigs: 
        p.update(pigs)
    
    # 繪製豬（現在只顯示豬圖片，不顯示房子）
    for p in pigs: 
        p.draw()
    
    if projectile:
        projectile.update()
        projectile.draw()
        if not projectile.active: projectile = None

    if game_phase == "playing":
        draw_sling()
        # 檢查是否還有豬存活
        alive_pigs = [p for p in pigs if p.alive]
        if not alive_pigs or (shots_fired >= MAX_SHOTS and projectile is None):
            game_phase, game_over_countdown = "game_over", 90
            send_score()
    elif game_phase == "game_over":
        ctx.fillStyle = "rgba(0, 0, 0, 0.7)"
        ctx.fillRect(0, 0, WIDTH, HEIGHT)
        ctx.fillStyle, ctx.textAlign = "white", "center"
        ctx.font = "40px Arial"
        ctx.fillText("游戏结束", WIDTH // 2, HEIGHT // 2 - 20)
        ctx.fillText(f"最终分数：{total_score}", WIDTH // 2, HEIGHT // 2 + 30)
        game_over_countdown -= 1
        if game_over_countdown <= 0: start_new_game()

timer.set_interval(loop, 30)
start_new_game()
