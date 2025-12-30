from browser import document, html, timer, ajax, window
from random import random
import time

canvas = document["gameCanvas"]
ctx = canvas.getContext("2d")
WIDTH, HEIGHT = 800, 400

# --- 圖片處理：確保載入完成 ---
bird_img = html.IMG(src="/static/images/bird.png")
pig_img = html.IMG(src="/static/images/pig.png")

# 遊戲常數
SLING_X, SLING_Y = 120, 300
MAX_SHOTS = 10

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

    def draw(self):
        if self.alive:
            ctx.fillStyle = "saddlebrown"
            for rx, ry, rw, rh in self.house_blocks:
                ctx.fillRect(self.x + rx - 40 * self.size_factor, self.y + ry, rw, rh)
            # 只有當圖片載入後才繪製
            if pig_img.complete:
                # 根據大小調整圖片尺寸
                ctx.drawImage(pig_img, self.x, self.y, self.w, self.h)

    def hit(self, px, py):
        return self.alive and self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

    def relocate(self, other_pigs):
        MIN_DISTANCE = 120
        MIN_X, MAX_X = 450, WIDTH - self.w - 120
        MIN_Y, MAX_Y = 200, HEIGHT - self.h - 15
        for _ in range(50): # 限制嘗試次數防止死循環
            new_x = MIN_X + random() * (MAX_X - MIN_X)
            new_y = MIN_Y + random() * (MAX_Y - MIN_Y)
            too_close = any(abs(new_x - p.x) < MIN_DISTANCE and abs(new_y - p.y) < MIN_DISTANCE 
                            for p in other_pigs if p is not self and p.alive)
            if not too_close:
                self.x, self.y = new_x, new_y
                self.last_hit_time = time.time()  # 重置計時器
                break

    def update(self, other_pigs):
        if not self.alive:
            return
            
        # 檢查是否超過30秒沒被擊中
        current_time = time.time()
        if current_time - self.last_hit_time > 30:  # 30秒
            self.relocate(other_pigs)
            
        # 增加閒置計時器的隨機移動效果（更自然的移動）
        self.idle_timer += 1
        if self.idle_timer > 60:  # 每60幀檢查一次隨機移動
            if random() < 0.1:  # 10%機率觸發小範圍隨機移動
                self.x += (random() - 0.5) * 20
                self.y += (random() - 0.5) * 10
                # 確保不會移出邊界
                self.x = max(450, min(WIDTH - self.w - 120, self.x))
                self.y = max(200, min(HEIGHT - self.h - 15, self.y))
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
    # 建立6隻豬，每隻大小不同（最大不超過1.5倍）
    pigs = []
    for i in range(6):
        # 創建不同大小的豬，從0.8倍到1.5倍
        size_factor = 0.8 + (i / 5) * 0.7  # 均勻分布從0.8到1.5
        pig = Pig(0, 0, size_factor)
        pigs.append(pig)
    
    # 初始位置
    for p in pigs: 
        p.relocate(pigs)

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

def draw_pig_info():
    # 顯示豬的閒置時間資訊（除錯用）
    ctx.fillStyle = "white"
    ctx.font = "12px Arial"
    for i, pig in enumerate(pigs):
        if pig.alive:
            idle_time = time.time() - pig.last_hit_time
            ctx.fillText(f"P{i+1}: {int(30 - idle_time)}s", pig.x, pig.y - 5)

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
    
    # 更新每隻豬的狀態
    for p in pigs: 
        p.update(pigs)
    
    # 繪製豬
    for p in pigs: 
        p.draw()
    
    # 繪製豬的閒置時間資訊（可選）
    # draw_pig_info()
    
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
        ctx.fillText("Game Over", WIDTH // 2, HEIGHT // 2 - 20)
        ctx.fillText(f"Score: {total_score}", WIDTH // 2, HEIGHT // 2 + 30)
        game_over_countdown -= 1
        if game_over_countdown <= 0: start_new_game()

timer.set_interval(loop, 30)
start_new_game()
