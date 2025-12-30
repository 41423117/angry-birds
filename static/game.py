from browser import document, html, timer, ajax, window
from random import random, uniform
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

# 新增：遊戲開始時間
game_start_time = None

# ------------------------------------------
# 類別 - 修改Pig類別
# ------------------------------------------
class Pig:
    def __init__(self, x, y, size_multiplier=1.0):
        self.x, self.y = x, y
        self.size_multiplier = size_multiplier
        # 根據倍數調整大小，最大不超過1.5倍
        base_size = 40
        self.w = base_size * size_multiplier
        self.h = base_size * size_multiplier
        self.alive = True
        # 調整房子塊的大小，使其與豬的大小成比例
        self.house_blocks = [
            (0, self.h, 120 * size_multiplier, 15 * size_multiplier),
            (0, -10 * size_multiplier, 15 * size_multiplier, 50 * size_multiplier),
            (105 * size_multiplier, -10 * size_multiplier, 15 * size_multiplier, 50 * size_multiplier),
            (0, -25 * size_multiplier, 120 * size_multiplier, 15 * size_multiplier)
        ]
        # 新增：記錄最後移動時間
        self.last_move_time = None
        # 新增：是否正在隨機移動
        self.is_moving_randomly = False
        # 新增：隨機移動的速度
        self.random_vx = 0
        self.random_vy = 0
        
    def draw(self):
        if self.alive:
            ctx.fillStyle = "saddlebrown"
            for rx, ry, rw, rh in self.house_blocks:
                ctx.fillRect(self.x + rx - 40 * self.size_multiplier, self.y + ry, rw, rh)
            # 只有當圖片載入後才繪製
            if pig_img.complete:
                ctx.drawImage(pig_img, self.x, self.y, self.w, self.h)
                
            # 新增：如果超過30秒沒被殺死，顯示提示
            if self.last_move_time and not self.is_moving_randomly:
                current_time = time.time()
                if current_time - self.last_move_time > 25:  # 接近30秒時顯示警告
                    ctx.fillStyle = "rgba(255, 165, 0, 0.7)"
                    ctx.beginPath()
                    ctx.arc(self.x + self.w/2, self.y - 20, 15, 0, 2 * 3.14159)
                    ctx.fill()
                    ctx.fillStyle = "white"
                    ctx.font = "bold 12px Arial"
                    ctx.textAlign = "center"
                    ctx.fillText("!", self.x + self.w/2, self.y - 15)

    def hit(self, px, py):
        return self.alive and self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

    def relocate(self, other_pigs):
        MIN_DISTANCE = 120 * max(1.0, self.size_multiplier)
        MIN_X, MAX_X = 450, WIDTH - self.w - 120
        MIN_Y, MAX_Y = 200, HEIGHT - self.h - 15
        for _ in range(50): # 限制嘗試次數防止死循環
            new_x = MIN_X + random() * (MAX_X - MIN_X)
            new_y = MIN_Y + random() * (MAX_Y - MIN_Y)
            too_close = any(abs(new_x - p.x) < MIN_DISTANCE and abs(new_y - p.y) < MIN_DISTANCE 
                            for p in other_pigs if p is not self and p.alive)
            if not too_close:
                self.x, self.y = new_x, new_y
                self.last_move_time = time.time()  # 重置移動時間
                self.is_moving_randomly = False    # 重置移動狀態
                break
    
    # 新增：檢查是否需要隨機移動
    def check_and_move_randomly(self):
        if not self.alive or self.is_moving_randomly:
            return False
            
        current_time = time.time()
        if self.last_move_time and current_time - self.last_move_time > 30:  # 超過30秒
            self.start_random_movement()
            return True
        return False
    
    # 新增：開始隨機移動
    def start_random_movement(self):
        self.is_moving_randomly = True
        # 隨機方向的速度
        self.random_vx = uniform(-2.0, 2.0)
        self.random_vy = uniform(-2.0, 2.0)
    
    # 新增：更新隨機移動
    def update_random_movement(self):
        if not self.alive or not self.is_moving_randomly:
            return
            
        # 更新位置
        self.x += self.random_vx
        self.y += self.random_vy
        
        # 邊界檢查
        MIN_X, MAX_X = 450, WIDTH - self.w - 20
        MIN_Y, MAX_Y = 150, HEIGHT - self.h - 15
        
        if self.x < MIN_X or self.x > MAX_X:
            self.random_vx = -self.random_vx  # 反彈
            self.x = max(MIN_X, min(MAX_X, self.x))  # 保持在範圍內
            
        if self.y < MIN_Y or self.y > MAX_Y:
            self.random_vy = -self.random_vy  # 反彈
            self.y = max(MIN_Y, min(MAX_Y, self.y))  # 保持在範圍內
        
        # 隨機改變方向（有一定機率）
        if random() < 0.02:  # 2%的機率改變方向
            self.random_vx = uniform(-2.0, 2.0)
            self.random_vy = uniform(-2.0, 2.0)

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
                total_score += 50
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
    global pigs, game_start_time
    # 建立6隻豬，大小不同，最大不超過1.5倍
    size_multipliers = [uniform(0.7, 1.5) for _ in range(6)]
    # 確保至少有一隻是正常大小
    size_multipliers[0] = 1.0
    
    pigs = []
    for i in range(6):
        # 建立豬時傳入大小倍數
        pig = Pig(0, 0, size_multipliers[i])
        pigs.append(pig)
    
    # 初始位置安排
    for p in pigs: 
        p.relocate(pigs)
        p.last_move_time = time.time()  # 初始化移動時間
    
    # 記錄遊戲開始時間
    game_start_time = time.time()

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
    
    # 更新和繪製豬
    for p in pigs:
        if p.alive:
            # 檢查是否需要開始隨機移動
            p.check_and_move_randomly()
            # 更新隨機移動
            p.update_random_movement()
        p.draw()
    
    # 更新和繪製鳥
    if projectile:
        projectile.update()
        projectile.draw()
        if not projectile.active: 
            projectile = None

    if game_phase == "playing":
        draw_sling()
        
        # 繪製豬的計時器（可選功能，顯示每隻豬的存活時間）
        ctx.fillStyle = "black"
        ctx.font = "12px Arial"
        for i, p in enumerate(pigs):
            if p.alive and p.last_move_time:
                elapsed = time.time() - p.last_move_time
                if elapsed > 20:  # 20秒後顯示倒數
                    time_left = max(0, 30 - elapsed)
                    ctx.fillText(f"{int(time_left)}s", p.x, p.y - 30)
        
        if shots_fired >= MAX_SHOTS and projectile is None:
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
        if game_over_countdown <= 0: 
            start_new_game()

timer.set_interval(loop, 30)
start_new_game()
