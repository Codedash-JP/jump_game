# Files

Below are two files:

1. `app.py`
2. `requirements.txt`

---

## app.py

```python
import streamlit as st
from textwrap import dedent

st.set_page_config(page_title="Mini Mario (Streamlit)", layout="centered")
st.title("🍄 Mini Mario — Streamlit Edition")
st.caption("Arrow keys to move/jump. Collect coins, avoid enemies, reach the flag!")

# Make the canvas a bit taller on wide screens
canvas_height = 640

html = dedent(f"""
<div id="game-root" style="width: 100%; height: {canvas_height}px;"></div>
<script src="https://cdn.jsdelivr.net/npm/phaser@3/dist/phaser.min.js"></script>
<script>
(() => {{
  const W = Math.min(window.innerWidth * 0.95, 1200);
  const H = {canvas_height};

  const levelWidth = 4200; // pixels
  const groundY = H - 80;

  let score = 0;

  const config = {{
    type: Phaser.AUTO,
    width: W,
    height: H,
    parent: 'game-root',
    physics: {{
      default: 'arcade',
      arcade: {{ gravity: {{ y: 1200 }}, debug: false }}
    }},
    scene: {{ preload, create, update }}
  }};

  let cursors, player, platforms, coins, enemies, flag, scoreText, tipText;

  function makeRectTexture(scene, key, w, h, color) {{
    const g = scene.add.graphics();
    g.fillStyle(color, 1);
    g.fillRoundedRect(0, 0, w, h, Math.min(w,h)*0.15);
    g.generateTexture(key, w, h);
    g.destroy();
  }}

  function makeCircleTexture(scene, key, r, color) {{
    const g = scene.add.graphics();
    g.fillStyle(color, 1);
    g.fillCircle(r, r, r);
    g.generateTexture(key, r*2, r*2);
    g.destroy();
  }}

  function preload() {{
    // Generate minimal textures so we don't load any assets
    makeRectTexture(this, 'player', 36, 40, 0xE74C3C); // red
    makeRectTexture(this, 'block', 64, 32, 0x2ECC71);  // green
    makeRectTexture(this, 'brick', 48, 24, 0x8E44AD);  // purple
    makeRectTexture(this, 'flag', 20, 80, 0x3498DB);   // blue
    makeCircleTexture(this, 'coin', 10, 0xF1C40F);     // yellow
    makeRectTexture(this, 'enemy', 32, 28, 0x2C3E50);  // dark
  }}

  function createGroundWithGaps(scene) {{
    const group = scene.physics.add.staticGroup();
    // Lay base ground, creating occasional gaps
    const tileW = 64;
    for (let x = 0; x < levelWidth; x += tileW) {{
      const gap = (x > 300 && x % 700 < 120) || (x > 1500 && x % 900 < 100);
      if (!gap) {{
        const b = group.create(x + tileW/2, groundY, 'block');
        b.refreshBody();
      }}
    }
    // Add some elevated platforms
    const elevs = [
      {{x: 500, y: groundY-140}},
      {{x: 700, y: groundY-220}},
      {{x: 1050, y: groundY-160}},
      {{x: 1600, y: groundY-200}},
      {{x: 2100, y: groundY-140}},
      {{x: 2600, y: groundY-220}},
      {{x: 3050, y: groundY-160}},
      {{x: 3550, y: groundY-200}}
    ];
    elevs.forEach(p => {{
      const s = group.create(p.x, p.y, 'brick');
      s.refreshBody();
    }});
    return group;
  }}

  function createCoins(scene) {{
    const grp = scene.physics.add.group();
    for (let x = 250; x < levelWidth - 200; x += 220) {{
      const y = groundY - 150 - (Math.sin(x/240) * 60);
      const c = grp.create(x, y, 'coin');
      c.setBounce(0.3);
      c.setCircle(10);
      c.body.setAllowGravity(false);
    }}
    return grp;
  }}

  function createEnemies(scene) {{
    const grp = scene.physics.add.group();
    const positions = [600, 1300, 1900, 2400, 3000, 3600];
    positions.forEach((x, i) => {{
      const e = grp.create(x, groundY-40, 'enemy');
      e.setCollideWorldBounds(false);
      e.setVelocityX(i % 2 === 0 ? 80 : -80);
      e.patrolLeft = x - 120;
      e.patrolRight = x + 120;
      e.body.setSize(28, 24); // tighter hitbox
    }});
    return grp;
  }}

  function create() {{
    // Level world bounds larger than viewport
    this.cameras.main.setBounds(0, 0, levelWidth, H);
    this.physics.world.setBounds(0, 0, levelWidth, H);

    platforms = createGroundWithGaps(this);

    player = this.physics.add.sprite(80, groundY-120, 'player');
    player.setBounce(0.05);
    player.setCollideWorldBounds(true);
    player.body.setSize(26, 36).setOffset(5, 4);

    coins = createCoins(this);
    enemies = createEnemies(this);

    // Finish flag
    flag = this.physics.add.staticImage(levelWidth - 80, groundY - 40, 'flag');

    // Camera follow
    this.cameras.main.startFollow(player, true, 0.1, 0.1);

    // Colliders & overlaps
    this.physics.add.collider(player, platforms);
    this.physics.add.collider(enemies, platforms);
    this.physics.add.collider(enemies, enemies);
    this.physics.add.overlap(player, coins, (pl, coin) => {{
      coin.disableBody(true, true);
      score += 1;
      scoreText.setText('Coins: ' + score);
    }});
    this.physics.add.overlap(player, flag, () => win(this));
    this.physics.add.overlap(player, enemies, () => die(this));

    // UI
    scoreText = this.add.text(12, 12, 'Coins: 0', {{ fontFamily: 'monospace', fontSize: '18px', backgroundColor: 'rgba(0,0,0,0.35)', padding: 6 }}).setScrollFactor(0);
    tipText = this.add.text(12, 40, '← → move   ↑ jump', {{ fontFamily: 'monospace', fontSize: '16px', backgroundColor: 'rgba(0,0,0,0.25)', padding: 6 }}).setScrollFactor(0);

    cursors = this.input.keyboard.createCursorKeys();
  }}

  function die(scene) {{
    scene.physics.pause();
    scene.add.text(player.x-80, player.y-40, 'GAME OVER', {{ fontFamily: 'monospace', fontSize: '28px', color: '#ff5555' }}).setScrollFactor(0);
    setTimeout(() => scene.scene.restart(), 1200);
  }}

  function win(scene) {{
    scene.physics.pause();
    scene.add.text(player.x-60, player.y-60, 'YOU WIN!', {{ fontFamily: 'monospace', fontSize: '28px', color: '#55ff55' }}).setScrollFactor(0);
  }}

  function update() {{
    // Enemy patrol logic
    enemies.children.iterate(e => {{
      if (!e) return;
      if (e.x < e.patrolLeft) {{ e.setVelocityX(90); }}
      if (e.x > e.patrolRight) {{ e.setVelocityX(-90); }}
    }});

    // Basic platformer controls
    const onGround = player.body.blocked.down;

    if (cursors.left.isDown) {{
      player.setVelocityX(-210);
      player.flipX = true;
    }} else if (cursors.right.isDown) {{
      player.setVelocityX(210);
      player.flipX = false;
    }} else {{
      player.setVelocityX(0);
    }}

    if ((cursors.up.isDown || cursors.space?.isDown) && onGround) {{
      player.setVelocityY(-460);
    }}

    // If player falls
    if (player.y > H + 100) {{ die(this); }}
  }}

  new Phaser.Game(config);
}})();
</script>
""")

st.components.v1.html(html, height=canvas_height, scrolling=False)

st.divider()
st.write(
    "Tip: If the canvas doesn’t fit, try the ‘wide’ layout in the page menu (top-right). "
    "This game is 100% client-side and embedded with Phaser.js via Streamlit components."
)
```

---

## requirements.txt

```txt
streamlit>=1.34
```
