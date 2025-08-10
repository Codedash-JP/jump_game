import streamlit as st

st.set_page_config(page_title="Mini Mario (Streamlit)", layout="centered")
st.title("🍄 Mini Pixel Runner — Streamlit Edition")
st.caption("Arrow keys: ← → move / ↑ or Space: jump. Pixel-art style, smoother camera.")

# Taller canvas so bottom area is always visible in Streamlit
CANVAS_HEIGHT = 760

# No f-strings here; JS uses braces freely
html = """
<style>
  /* Make Phaser canvas render crisp pixels */
  #game-root canvas { image-rendering: pixelated; image-rendering: crisp-edges; }
</style>
<div id="game-root" style="width: 100%; height: 760px;"></div>
<script src="https://cdn.jsdelivr.net/npm/phaser@3/dist/phaser.min.js"></script>
<script>
(() => {
  const root = document.getElementById('game-root');
  const H = root.clientHeight || 760;
  const W = Math.min(window.innerWidth * 0.98, 1200);

  const levelWidth = 4600; // longer level
  const groundY = H - 88;  // a little lower so ground fully visible

  let score = 0;

  const config = {
    type: Phaser.AUTO,
    width: W,
    height: H,
    parent: 'game-root',
    backgroundColor: '#87CEEB', // sky
    physics: { default: 'arcade', arcade: { gravity: { y: 1300 }, debug: false } },
    scene: { preload, create, update }
  };

  let cursors, player, platforms, coins, enemies, flag, scoreText;

  // --- Pixel-art helpers ----------------------------------------------------
  function drawPixelTexture(scene, key, pixels, scale, palette) {
    const g = scene.add.graphics();
    pixels.forEach((row, y) => {
      row.forEach((pi, x) => {
        if (pi === -1) return;
        g.fillStyle(palette[pi], 1);
        g.fillRect(x * scale, y * scale, scale, scale);
      });
    });
    const w = pixels[0].length * scale;
    const h = pixels.length * scale;
    g.generateTexture(key, w, h);
    g.destroy();
  }

  function preload() {
    // Player: 16x16 cute pixel hero (palette indices)
    const pal = [0x2b2d42, 0xff595e, 0xffca3a, 0x8ac926, 0xffffff, 0x1982c4, 0x6a4c93];
    const P = -1; // transparent
    const hero = [
      [P,P,1,1,1,1,1,1,1,1,1,P,P,P,P],
      [P,1,1,1,1,1,1,1,1,1,1,1,P,P,P],
      [1,1,1,1,4,4,4,4,4,4,1,1,1,P,P],
      [1,1,4,4,4,5,5,5,5,4,4,4,1,1,P],
      [1,4,4,5,5,5,5,5,5,5,5,4,4,1,P],
      [1,4,5,5,5,5,5,5,5,5,5,5,4,1,P],
      [1,4,5,5,2,2,2,2,2,2,5,5,4,1,P],
      [P,4,5,2,2,2,2,2,2,2,2,5,4,P,P],
      [P,4,5,2,3,3,2,2,3,3,2,5,4,P,P],
      [P,1,4,5,2,2,2,2,2,2,5,4,1,P,P],
      [P,P,1,4,4,5,5,5,5,4,4,1,P,P,P],
      [P,P,1,1,1,0,0,0,0,1,1,1,P,P,P],
      [P,P,1,1,0,0,0,0,0,0,1,1,P,P,P],
      [P,P,1,1,0,0,0,0,0,0,1,1,P,P,P],
      [P,P,1,1,0,P,P,P,P,0,1,1,P,P,P],
      [P,P,0,0,0,P,P,P,P,0,0,0,P,P,P]
    ];
    drawPixelTexture(this, 'hero_idle', hero, 3, pal);

    // Simple enemy (slime)
    const slime = [
      [P,P,P,6,6,6,6,6,P,P,P],
      [P,P,6,6,6,6,6,6,6,P,P],
      [P,6,6,6,6,6,6,6,6,6,P],
      [6,6,6,6,6,6,6,6,6,6,6],
      [6,6,6,5,5,5,5,5,6,6,6],
      [P,6,5,P,P,P,P,P,5,6,P],
      [P,P,5,5,5,5,5,5,5,P,P]
    ];
    drawPixelTexture(this, 'slime', slime, 3, pal);

    // Coin
    const coin = [
      [P,P,2,2,2,2,P,P],
      [P,2,2,2,2,2,2,P],
      [2,2,2,2,2,2,2,2],
      [2,2,2,2,2,2,2,2],
      [P,2,2,2,2,2,2,P],
      [P,P,2,2,2,2,P,P]
    ];
    drawPixelTexture(this, 'coin_px', coin, 3, pal);

    // Ground tiles
    const gpal = [0x3b7a57, 0x2e5a3a, 0x7f5539, 0x5e3b2e];
    const grass = [
      [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
      [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
      [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
      [2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2]
    ];
    drawPixelTexture(this, 'tile_grass', grass, 4, gpal);

    // Flag
    const fpal = [0x1e88e5, 0x1b5e20, 0xffffff];
    const flag = [
      [P,P,P,1,1,1,P,P,P],
      [P,P,P,1,2,1,P,P,P],
      [P,P,P,1,2,1,P,P,P],
      [P,P,P,1,2,1,P,P,P],
      [P,P,P,1,2,1,P,P,P],
      [P,P,P,1,2,1,P,P,P],
      [P,P,P,1,2,1,P,P,P],
      [P,P,P,1,2,1,P,P,P],
      [P,P,P,1,2,1,P,P,P],
      [P,P,P,1,2,1,P,P,P],
      [P,P,P,1,2,1,P,P,P],
      [P,P,P,1,2,1,P,P,P],
      [P,P,P,1,2,1,P,P,P],
      [P,P,P,1,2,1,P,P,P],
      [P,P,P,1,2,1,P,P,P]
    ];
    drawPixelTexture(this, 'flag_px', flag, 3, fpal);
  }

  function buildGround(scene) {
    const group = scene.physics.add.staticGroup();
    const tileW = 64; // after scaling
    for (let x = 0; x < levelWidth; x += tileW) {
      // Create gaps occasionally
      const gap = (x > 400 && x % 800 < 140) || (x > 1800 && x % 1000 < 120);
      if (!gap) {
        const t = group.create(x + tileW/2, groundY, 'tile_grass');
        t.refreshBody();
      }
    }
    // Some floating platforms
    const elevs = [
      {x: 520, y: groundY-160},
      {x: 860, y: groundY-230},
      {x: 1320, y: groundY-170},
      {x: 1880, y: groundY-210},
      {x: 2400, y: groundY-140},
      {x: 2920, y: groundY-220},
      {x: 3380, y: groundY-160},
      {x: 3920, y: groundY-210}
    ];
    elevs.forEach(p => { const s = group.create(p.x, p.y, 'tile_grass'); s.refreshBody(); });
    return group;
  }

  function createCoins(scene) {
    const grp = scene.physics.add.group();
    for (let x = 300; x < levelWidth - 200; x += 240) {
      const y = groundY - 160 - (Math.sin(x/250) * 60);
      const c = grp.create(x, y, 'coin_px');
      c.setCircle(12);
      c.setBounce(0.2);
      c.body.setAllowGravity(false);
    }
    return grp;
  }

  function createEnemies(scene) {
    const grp = scene.physics.add.group();
    const positions = [700, 1500, 2100, 2700, 3300, 4100];
    positions.forEach((x, i) => {
      const e = grp.create(x, groundY-36, 'slime');
      e.setVelocityX(i % 2 === 0 ? 70 : -70);
      e.patrolLeft = x - 120;
      e.patrolRight = x + 120;
      e.body.setSize(42, 18).setOffset(5, 20);
    });
    return grp;
  }

  function create() {
    // World bounds and camera
    this.cameras.main.setBounds(0, 0, levelWidth, H);
    this.physics.world.setBounds(0, 0, levelWidth, H);

    // Parallax clouds
    const cloud = this.add.graphics();
    cloud.fillStyle(0xffffff, 0.6);
    for (let i=0; i<12; i++) {
      const x = i * 380 + 100 * Math.random();
      const y = 60 + 120 * Math.random();
      cloud.fillCircle(x, y, 24);
      cloud.fillCircle(x+24, y+10, 20);
      cloud.fillCircle(x-22, y+12, 18);
    }
    cloud.setScrollFactor(0.5);

    platforms = buildGround(this);

    player = this.physics.add.sprite(80, groundY-120, 'hero_idle');
    player.setCollideWorldBounds(true);
    player.body.setSize(36, 42).setOffset(6, 6);

    coins = createCoins(this);
    enemies = createEnemies(this);

    flag = this.physics.add.staticImage(levelWidth - 80, groundY - 48, 'flag_px');

    // Camera follow with mild zoom and offset to show more bottom area
    const cam = this.cameras.main;
    cam.startFollow(player, true, 0.12, 0.12);
    cam.setZoom(1.6);
    cam.setFollowOffset(0, 80); // push player upward in view -> more bottom visible

    // Colliders & overlaps
    this.physics.add.collider(player, platforms);
    this.physics.add.collider(enemies, platforms);
    this.physics.add.collider(enemies, enemies);
    this.physics.add.overlap(player, coins, (pl, coin) => { coin.disableBody(true, true); score += 1; scoreText.setText('Coins: ' + score); });
    this.physics.add.overlap(player, flag, () => win(this));
    this.physics.add.overlap(player, enemies, () => die(this));

    // UI
    scoreText = this.add.text(12, 12, 'Coins: 0', { fontFamily: 'monospace', fontSize: '18px', backgroundColor: 'rgba(0,0,0,0.35)', padding: 6 }).setScrollFactor(0);

    // Controls
    cursors = this.input.keyboard.createCursorKeys();
  }

  function die(scene) {
    scene.physics.pause();
    scene.add.text(player.x-80, player.y-40, 'GAME OVER', { fontFamily: 'monospace', fontSize: '28px', color: '#ff5555' });
    setTimeout(() => scene.scene.restart(), 1100);
  }

  function win(scene) {
    scene.physics.pause();
    scene.add.text(player.x-60, player.y-60, 'YOU WIN!', { fontFamily: 'monospace', fontSize: '28px', color: '#55ff55' });
  }

  function update() {
    // Enemy patrol logic
    enemies.children.iterate(e => {
      if (!e) return;
      if (e.x < e.patrolLeft) { e.setVelocityX(80); }
      if (e.x > e.patrolRight) { e.setVelocityX(-80); }
    });

    const onGround = player.body.blocked.down;

    if (cursors.left.isDown) {
      player.setVelocityX(-210);
      player.flipX = true;
    } else if (cursors.right.isDown) {
      player.setVelocityX(210);
      player.flipX = false;
    } else {
      player.setVelocityX(0);
    }

    if ((cursors.up.isDown || (cursors.space && cursors.space.isDown)) && onGround) {
      player.setVelocityY(-470);
    }

    if (player.y > H + 100) { die(this); }
  }

  new Phaser.Game(config);
})();
</script>
"""

st.components.v1.html(html, height=CANVAS_HEIGHT, scrolling=False)

st.divider()
st.write(
    "Now pixel-art and taller canvas. If you still can’t see the bottom, switch to ‘wide’ layout from the page menu."
)
