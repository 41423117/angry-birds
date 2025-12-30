from browser import document, html, timer, ajax, window
from random import random
import time

canvas = document["gameCanvas"]
ctx = canvas.getContext("2d")

# 設定手機端適配的尺寸
WIDTH = min(window.innerWidth - 20, 800)  # 最大800px，但適應手機寬度
HEIGHT = min(window.innerHeight - 100, 500)  # 最大500px，但適應手機高度

# 更新畫布尺寸
canvas.width = WIDTH
canvas.height = HEIGHT
canvas.style.width = f"{WIDTH}px"
canvas.style.height = f"{HEIGHT}px"

# --- 圖片處理：確保載入完成 ---
bird_img = html.IMG(src="/static/images/bird.png")
pig_img = html.IMG(src="/static/images/pig.png")

# 遊戲常數 - 根據手機屏幕調整
SLING_X, SLING_Y = int(WIDTH * 0.15), int(HEIGHT * 0.75)  # 彈弓位置在左下角
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
touch_start_time = 0  # 用於防止誤觸

# ------------------------------------------
# 類別
# ------------------------------------------
class Pig:
    def __init__(self, x, y, size_factor=1.0):
        self.x, self.y = x, y
        # 根據手機屏幕調整大小
        base_size = int(30 * (min(WIDTH, HEIGHT) / 500))  # 基於屏幕尺寸調整
        self.size_factor = min(1.5, max(0.8, size_factor))
        self.w, self.h = int(base_size * self.size_factor), int(base_size * self.size_factor)
        self.alive = True
        
        # 根據大小調整房子的尺寸
        house_width = 90 * self.size_factor
        house_height = 40 * self.size_factor
        roof_thickness = 12 * self.size_factor
        wall_thickness = 12 * self.size_factor
        
        self.house_blocks = [
            (0, self.h, house_width, roof_thickness),
            (0, -roof_thickness, wall_thickness, house_height),
            (house_width - wall_thickness, -roof_thickness, wall_thickness, house_height),
            (0, -roof_thickness * 2, house_width, roof_thickness)
        ]
        self.last_hit_time = time.time()
        self.idle_timer = 0

    def draw(self):
        if self.alive:
            ctx.fillStyle = "saddlebrown"
            for rx, ry, rw, rh in self.house_blocks:
                ctx.fillRect(self.x + rx - 30 * self.size_factor, self.y + ry, rw, rh)
            if pig_img.complete:
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
        MAX_ATTEMPTS = 50
        MIN_X, MAX_X = int(WIDTH * 0.5), WIDTH - self.w - 50  # 右半邊區域
        MIN_Y, MAX_Y = int(HEIGHT * 0.3), HEIGHT - self.h - 20
        
        for attempt in range(MAX_ATTEMPTS):
            new_x = MIN_X + random() * (MAX_X - MIN_X)
            new_y = MIN_Y + random() * (MAX_Y - MIN_Y)
            
            old_x, old_y = self.x, self.y
            self.x, self.y = new_x, new_y
            
            collision = False
            for pig in other_pigs:
                if pig is not self and pig.alive and self.check_collision(pig):
                    collision = True
                    break
            
            if not collision:
                self.last_hit_time = time.time()
                return True
            
            self.x, self.y = old_x, old_y
        
        return self.find_grid_position(other_pigs, MIN_X, MAX_X, MIN_Y, MAX_Y)

    def find_grid_position(self, other_pigs, min_x, max_x, min_y, max_y):
        """在網格中尋找可用位置"""
        grid_size = 50
        
        cols = min(3, int((max_x - min_x) / grid_size))
        rows = min(2, int((max_y - min_y) / grid_size))
        
        for r in range(rows):
            for c in range(cols):
                new_x = min_x + c * grid_size + grid_size / 2 - self.w / 2
                new_y = min_y + r * grid_size + grid_size / 2 - self.h / 2
                
                old_x, old_y = self.x, self.y
                self.x, self.y = new_x, new_y
                
                collision = False
                for pig in other_pigs:
                    if pig is not self and pig.alive and self.check_collision(pig):
                        collision = True
                        break
                
                if not collision:
                    self.last_hit_time = time.time()
                    return True
                
                self.x, self.y = old_x, old_y
        
        self.x = min_x + random() * (max_x - min_x)
        self.y = min_y + random() * (max_y - min_y)
        self.last_hit_time = time.time()
        return False

    def update(self, other_pigs):
        if not self.alive:
            return
            
        current_time = time.time()
        if current_time - self.last_hit_time > 30:  # 30秒
            self.relocate(other_pigs)
            
        self.idle_timer += 1
        if self.idle_timer > 60:
            if random() < 0.05:
                old_x, old_y = self.x, self.y
                self.x += (random() - 0.5) * 15
                self.y += (random() - 0.5) * 8
                
                self.x = max(WIDTH * 0.5, min(WIDTH - self.w - 50, self.x))
                self.y = max(HEIGHT * 0.3, min(HEIGHT - self.h - 20, self.y))
                
                collision = False
                for pig in other_pigs:
                    if pig is not self and pig.alive and self.check_collision(pig):
                        collision = True
                        break
                
                if collision:
                    self.x, self.y = old_x, old_y
                
                self.idle_timer = 0

class Bird:
    def __init__(self, x, y, vx, vy):
        # 根據屏幕尺寸調整鳥的大小
        base_size = int(30 * (min(WIDTH, HEIGHT) / 500))
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.w, self.h = base_size, base_size
        self.active = True

    def update(self):
        global total_score
        if not self.active: 
            return
        self.vy += 0.25  # 重力調小一點，適應手機屏幕
        self.x += self.vx
        self.y += self.vy
        
        # 邊界檢查
        if (self.y > HEIGHT - self.h or 
            self.x > WIDTH or 
            self.x < 0 or
            self.y < 0):
            self.active = False
            
        for p in pigs:
            if p.hit(self.x + self.w / 2, self.y + self.h / 2):
                p.relocate(pigs)
                total_score += int(50 * p.size_factor)
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
    pigs = []
    
    # 為手機屏幕優化的初始位置
    original_positions = [
        (int(WIDTH * 0.6), int(HEIGHT * 0.4)),
        (int(WIDTH * 0.7), int(HEIGHT * 0.5)),
        (int(WIDTH * 0.8), int(HEIGHT * 0.3)),
        (int(WIDTH * 0.65), int(HEIGHT * 0.3)),
        (int(WIDTH * 0.75), int(HEIGHT * 0.4)),
        (int(WIDTH * 0.6), int(HEIGHT * 0.5))
    ]
    
    for i in range(6):
        size_factor = 0.8 + (i / 5) * 0.7
        pig = Pig(original_positions[i][0], original_positions[i][1], size_factor)
        pigs.append(pig)
    
    adjust_pig_positions()

def adjust_pig_positions():
    """調整豬的位置，確保它們不會重疊"""
    MAX_ATTEMPTS = 50
    MIN_X, MAX_X = int(WIDTH * 0.5), WIDTH - 60
    MIN_Y, MAX_Y = int(HEIGHT * 0.3), HEIGHT - 60
    
    for i in range(len(pigs)):
        pig = pigs[i]
        
        for attempt in range(MAX_ATTEMPTS):
            collision = False
            for j in range(len(pigs)):
                if i != j and pigs[j].alive and pig.check_collision(pigs[j]):
                    collision = True
                    break
            
            if not collision:
                break
            
            offset_x = (random() - 0.5) * 80
            offset_y = (random() - 0.5) * 60
            pig.x = max(MIN_X, min(MAX_X, pig.x + offset_x))
            pig.y = max(MIN_Y, min(MAX_Y, pig.y + offset_y))
        
        if collision:
            cols = 3
            rows = 2
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
    """處理手機觸控座標"""
    rect = canvas.getBoundingClientRect()
    
    # 針對手機觸控優化的座標計算
    if hasattr(evt, "touches") and len(evt.touches) > 0:
        client_x, client_y = evt.touches[0].clientX, evt.touches[0].clientY
    elif hasattr(evt, "changedTouches") and len(evt.changedTouches) > 0:
        client_x, client_y = evt.changedTouches[0].clientX, evt.changedTouches[0].clientY
    else:
        client_x, client_y = evt.clientX, evt.clientY
    
    # 計算實際畫布座標
    scale_x = canvas.width / rect.width
    scale_y = canvas.height / rect.height
    
    x = (client_x - rect.left) * scale_x
    y = (client_y - rect.top) * scale_y
    
    # 限制在畫布範圍內
    x = max(0, min(x, canvas.width))
    y = max(0, min(y, canvas.height))
    
    return x, y

def handle_touch_start(evt):
    """處理手機觸控開始"""
    global mouse_down, mouse_pos, touch_start_time
    evt.preventDefault()
    
    # 防止短時間多次觸發
    current_time = time.time()
    if current_time - touch_start_time < 0.3:  # 300ms防抖
        return
    
    touch_start_time = current_time
    
    if game_phase == "playing" and projectile is None and shots_fired < MAX_SHOTS:
        mouse_down = True
        mouse_pos = get_pos(evt)
        # 在手機上提供視覺反饋
        canvas.style.opacity = "0.9"

def handle_touch_move(evt):
    """處理手機觸控移動"""
    global mouse_pos
    evt.preventDefault()
    
    if mouse_down:
        mouse_pos = get_pos(evt)
        
        # 限制拖拽範圍，避免拖太遠
        mx, my = mouse_pos
        max_pull_distance = 150  # 最大拖拽距離
        dx, dy = SLING_X - mx, SLING_Y - my
        distance = (dx**2 + dy**2)**0.5
        
        if distance > max_pull_distance:
            ratio = max_pull_distance / distance
            mouse_pos = (
                SLING_X - dx * ratio,
                SLING_Y - dy * ratio
            )

def handle_touch_end(evt):
    """處理手機觸控結束"""
    global mouse_down, projectile, shots_fired
    evt.preventDefault()
    
    if mouse_down:
        mouse_down = False
        canvas.style.opacity = "1.0"  # 恢復正常透明度
        
        end_pos = get_pos(evt)
        dx, dy = SLING_X - end_pos[0], SLING_Y - end_pos[1]
        
        # 限制發射力量
        max_force = 80
        force = (dx**2 + dy**2)**0.5
        if force > max_force:
            ratio = max_force / force
            dx *= ratio
            dy *= ratio
        
        # 手機端調低發射速度
        projectile = Bird(SLING_X, SLING_Y, dx * 0.2, dy * 0.2)
        shots_fired += 1
        update_shots_remaining()

def handle_resize(_=None):
    """處理窗口大小變化"""
    global WIDTH, HEIGHT, SLING_X, SLING_Y
    
    # 更新畫布尺寸
    WIDTH = min(window.innerWidth - 20, 800)
    HEIGHT = min(window.innerHeight - 100, 500)
    
    canvas.width = WIDTH
    canvas.height = HEIGHT
    canvas.style.width = f"{WIDTH}px"
    canvas.style.height = f"{HEIGHT}px"
    
    # 更新彈弓位置
    SLING_X, SLING_Y = int(WIDTH * 0.15), int(HEIGHT * 0.75)
    
    # 重新初始化遊戲
    if game_phase == "playing":
        adjust_pig_positions()

# 綁定事件 - 針對手機優化
canvas.bind("mousedown", handle_touch_start)
canvas.bind("touchstart", handle_touch_start)
canvas.bind("touchmove", handle_touch_move)
canvas.bind("touchend", handle_touch_end)

# 綁定窗口大小變化事件
window.bind("resize", handle_resize)

# 初始調整大小
handle_resize()

# ------------------------------------------
# 繪圖與主迴圈
# ------------------------------------------
def draw_sling():
    if game_phase != "playing": 
        return
        
    ctx.strokeStyle = "rgba(139, 69, 19, 0.8)"  # 半透明的深棕色
    ctx.lineWidth = 3
    
    if mouse_down:
        mx, my = mouse_pos
        
        # 繪製橡皮筋
        ctx.beginPath()
        ctx.moveTo(SLING_X - 5, SLING_Y)
        ctx.lineTo(mx, my)
        ctx.stroke()
        
        ctx.beginPath()
        ctx.moveTo(SLING_X + 5, SLING_Y)
        ctx.lineTo(mx, my)
        ctx.stroke()
        
        # 繪製準備發射的鳥
        if bird_img.complete:
            ctx.drawImage(bird_img, mx - 15, my - 15, 30, 30)
        
        # 繪製力量指示器
        dx, dy = SLING_X - mx, SLING_Y - my
        force = (dx**2 + dy**2)**0.5
        
        if force > 10:
            ctx.beginPath()
            ctx.arc(SLING_X, SLING_Y, 5, 0, 2 * 3.14159)
            ctx.fillStyle = "rgba(255, 0, 0, 0.5)"
            ctx.fill()
            
            ctx.beginPath()
            ctx.moveTo(SLING_X, SLING_Y)
            ctx.lineTo(mx, my)
            ctx.strokeStyle = "rgba(255, 0, 0, 0.3)"
            ctx.lineWidth = 2
            ctx.stroke()
    
    elif projectile is None and shots_fired < MAX_SHOTS:
        if bird_img.complete:
            ctx.drawImage(bird_img, SLING_X - 15, SLING_Y - 15, 30, 30)

def send_score():
    global sent
    if sent: 
        return
    sent = True
    try:
        req = ajax.ajax()
        req.open("POST", "/submit_score", True)
        req.set_header("Content-Type", "application/json")
        req.send(window.JSON.stringify({"score": total_score}))
    except:
        pass  # 如果提交失敗，繼續遊戲

def loop():
    global projectile, game_phase, game_over_countdown
    
    # 清除畫布
    ctx.clearRect(0, 0, WIDTH, HEIGHT)
    
    # 繪製背景
    ctx.fillStyle = "#87CEEB"  # 天空藍
    ctx.fillRect(0, 0, WIDTH, HEIGHT * 0.7)
    
    ctx.fillStyle = "#8B4513"  # 土地棕
    ctx.fillRect(0, HEIGHT * 0.7, WIDTH, HEIGHT * 0.3)
    
    # 繪製彈弓架
    ctx.fillStyle = "#8B4513"
    ctx.fillRect(SLING_X - 15, SLING_Y - 40, 30, 60)
    ctx.fillRect(SLING_X - 30, SLING_Y, 60, 10)
    
    # 更新和繪製豬
    for p in pigs: 
        p.update(pigs)
    
    for p in pigs: 
        p.draw()
    
    # 更新和繪製鳥
    if projectile:
        projectile.update()
        projectile.draw()
        if not projectile.active: 
            projectile = None
    
    # 繪製彈弓和UI
    if game_phase == "playing":
        draw_sling()
        
        # 繪製分數和剩餘發射次數
        ctx.fillStyle = "white"
        ctx.font = "bold 20px Arial"
        ctx.fillText(f"分數: {total_score}", 10, 30)
        ctx.fillText(f"剩餘: {MAX_SHOTS - shots_fired}", 10, 60)
        
        # 檢查遊戲是否結束
        alive_pigs = [p for p in pigs if p.alive]
        if not alive_pigs or (shots_fired >= MAX_SHOTS and projectile is None):
            game_phase, game_over_countdown = "game_over", 90
            send_score()
    
    elif game_phase == "game_over":
        # 半透明黑色遮罩
        ctx.fillStyle = "rgba(0, 0, 0, 0.7)"
        ctx.fillRect(0, 0, WIDTH, HEIGHT)
        
        # 遊戲結束文字
        ctx.fillStyle = "white"
        ctx.textAlign = "center"
        ctx.font = "bold 32px Arial"
        ctx.fillText("遊戲結束", WIDTH // 2, HEIGHT // 2 - 40)
        
        ctx.font = "24px Arial"
        ctx.fillText(f"最終分數: {total_score}", WIDTH // 2, HEIGHT // 2)
        
        ctx.font = "18px Arial"
        ctx.fillText(f"{game_over_countdown // 30}秒後重新開始", WIDTH // 2, HEIGHT // 2 + 40)
        
        game_over_countdown -= 1
        if game_over_countdown <= 0: 
            start_new_game()

# 啟動遊戲迴圈
timer.set_interval(loop, 30)
start_new_game()

# 在手機瀏覽器上禁用滾動
document.body.style.overflow = "hidden"
document.body.style.touchAction = "none"

# 添加CSS樣式確保更好的觸控體驗
style = html.STYLE("""
    canvas {
        display: block;
        margin: 10px auto;
        border: 2px solid #333;
        border-radius: 10px;
        background-color: #f0f0f0;
        touch-action: none; /* 防止瀏覽器處理觸控手勢 */
    }
    body {
        margin: 0;
        padding: 0;
        background-color: #222;
        overflow: hidden;
        user-select: none; /* 防止文本選擇 */
        -webkit-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
    }
    @media (max-width: 600px) {
        canvas {
            margin: 5px auto;
            border-width: 1px;
        }
    }
""")
document.head <= style
