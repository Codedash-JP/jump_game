
import streamlit as st

st.set_page_config(page_title="Pixel Invaders (Streamlit)", layout="centered")
st.title("👾 Pixel Invaders — Streamlit Edition")
st.caption("← → move, Space to shoot. Cute pixel art. Clear all invaders!")

CANVAS_HEIGHT = 720

# Keep this as a plain string (no f-strings) so braces in JS don't break Python parsing
html = """
<style>
  #game-root canvas { image-rendering: pixelated; image-rendering: crisp-edges; }
</style>
<div id=\"game-root\" style=\"width: 100%; height: 720px;\"></div>
<script src=\"https://cdn.jsdelivr.net/npm/phaser@3/dist/phaser.min.js\"></script>
<script>
(() => {
  const root = document.getElementById('game-root');
  const H = root.clientHeight || 720;
  const W = Math.min(window.innerWidth * 0.98, 1100);

  const config = {
    type: Phaser.AUTO,
    width: W,
    height: H,
    parent: 'game-root',
    backgroundColor: '#1e2a38',
    physics: { default: 'arcade', arcade: { gravity: { y: 0 }, debug: false } },
    scene: { preload, create, update }
  };

  let cursors, shootKey, player, bullets, invaders, shields, enemyBullets;
  let scoreText, livesText, statusText;
  let gameOver = false, win = false;
  let lastShot = 0, shotCooldown = 250; // ms
  let invaderSpeed = 40; // px/sec base
  let dir = 1; // 1 -> right, -1 -> left

  // ---------- Pixel art helpers ----------
  function drawPixelTexture(scene, key, pixels, scale, palette) {
    const g = scene.add.graphics();
    for (let y = 0; y < pixels.length; y++) {
      for (let x = 0; x < pixels[y].length; x++) {
        const pi = pixels[y][x];
        if (pi === -1) continue;
        g.fillStyle(palette[pi], 1);
        g.fillRect(x * scale, y * scale, scale, scale);
      }
    }
    const w = pixels[0].length * scale;
    const h = pixels.length * scale;
    g.generateTexture(key, w, h);
    g.destroy();
  }

  function preload() {
    const P = -1;
    // Cute pastel palette
    const pal = [0xffffff, 0xffc6ff, 0xbdb2ff, 0xa0c4ff, 0x9bf6ff, 0xcaffbf, 0xfdffb6, 0xffadad, 0xffd6a5, 0x90a4ae, 0x263238];

    // Player ship (16x12)
    const ship = [
      [P,P,P,P,P,1,1,1,1,1,P,P,P,P,P],
      [P,P,P,1,1,1,1,1,1,1,1,1,P,P,P],
      [P,P,1,1,1,2,2,2,2,2,1,1,1,P,P],
      [P,1,1,2,2,2,2,3,2,2,2,2,1,1,P],
      [1,1,2,2,2,2,3,3,3,2,2,2,2,1,1],
      [1,2,2,2,2,3,3,4,3,3,2,2,2,2,1],
      [P,P,P,P,2,2,3,4,3,2,2,P,P,P,P],
      [P,P,P,P,P,2,3,3,3,2,P,P,P,P,P],
      [P,P,P,P,P,P,2,2,2,P,P,P,P,P,P],
      [P,P,P,P,P,P,P,2,P,P,P,P,P,P,P],
      [P,P,P,P,P,P,2,2,2,P,P,P,P,P,P],
      [P,P,P,P,P,P,2,P,2,P,P,P,P,P,P]
    ];
    drawPixelTexture(this, 'ship', ship, 3, pal);

    // Invader (12x10)
    const inv = [
      [P,P,7,7,P,P,P,P,7,7,P,P],
      [P,7,7,7,7,P,P,7,7,7,7,P],
      [7,7,6,7,7,7,7,7,7,6,7,7],
      [7,7,7,7,7,7,7,7,7,7,7,7],
      [P,7,7,P,7,7,7,7,P,7,7,P],
      [P,7,7,7,7,7,7,7,7,7,7,P],
      [P,P,7,7,7,7,7,7,7,7,P,P],
      [P,P,7,P,P,P,P,P,P,7,P,P],
      [P,7,P,P,P,P,P,P,P,P,7,P],
      [P,P,7,7,P,P,P,P,7,7,P,P]
    ];
    drawPixelTexture(this, 'invader', inv, 3, pal);

    // Enemy bullet & player bullet (tiny)
    const bulletPix = [ [0] ];
    drawPixelTexture(this, 'pbullet', bulletPix, 4, [0xffff00]);
    drawPixelTexture(this, 'ebullet', bulletPix, 4, [0xff6b6b]);

    // Shield block (8x8)
    const shield = [
      [9,9,9,9,9,9,9,9],
      [9,9,9,9,9,9,9,9],
      [9,9,9,9,9,9,9,9],
      [9,9,9,9,9,9,9,9],
      [9,9,9,9,9,9,9,9],
      [9,9,9,9,9,9,9,9],
      [9,9,9,9,9,9,9,9],
      [9,9,9,9,9,9,9,9]
    ];
    drawPixelTexture(this, 'shield', shield, 4, pal);
  }

  function create() {
    // Stars background (cute twinkles)
    const stars = this.add.graphics();
    for (let i=0; i<120; i++) {
      const x = Math.random() * W;
      const y = Math.random() * H;
      const a = 0.3 + Math.random() * 0.5;
      stars.fillStyle(0xffffff, a);
      stars.fillRect(x, y, 2, 2);
    }

    // Groups
    bullets = this.physics.add.group({ maxSize: 6 });
    enemyBullets = this.physics.add.group({ maxSize: 6 });
    invaders = this.physics.add.group();
    shields = this.physics.add.staticGroup();

    // Player
    player = this.physics.add.sprite(W/2, H - 80, 'ship');
    player.setCollideWorldBounds(true);
    player.lives = 3;

    // Build invader grid
    const rows = 5, cols = 10;
    const startX = 80, startY = 110, gapX = 64, gapY = 48;
    for (let r=0; r<rows; r++) {
      for (let c=0; c<cols; c++) {
        const inv = invaders.create(startX + c*gapX, startY + r*gapY, 'invader');
        inv.setImmovable(true);
        inv.body.allowGravity = false;
        inv.row = r; inv.col = c;
      }
    }

    // Shields (three bunkers)
    const bunkerY = H - 160;
    [W*0.25, W*0.5, W*0.75].forEach(cx => {
      for (let i=-3; i<=3; i++) {
        for (let j=0; j<3; j++) {
          const b = shields.create(cx + i*18, bunkerY + j*18, 'shield');
          b.refreshBody();
        }
      }
    });

    // UI
    scoreText = this.add.text(12, 12, 'Score: 0', { fontFamily: 'monospace', fontSize: '18px', color: '#ffffff', backgroundColor: 'rgba(0,0,0,0.35)', padding: 6 });
    livesText = this.add.text(W - 160, 12, 'Lives: 3', { fontFamily: 'monospace', fontSize: '18px', color: '#ffffff', backgroundColor: 'rgba(0,0,0,0.35)', padding: 6 }).setOrigin(0,0);

    statusText = this.add.text(W/2, H/2, '', { fontFamily: 'monospace', fontSize: '28px', color: '#ffd6a5' }).setOrigin(0.5);

    // Controls
    cursors = this.input.keyboard.createCursorKeys();
    shootKey = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.SPACE);

    // Collisions
    this.physics.add.overlap(bullets, invaders, (b, inv) => { b.destroy(); inv.destroy(); addScore(10); checkWin(this); });
    this.physics.add.collider(bullets, shields, (b, s) => { b.destroy(); s.destroy(); });
    this.physics.add.collider(enemyBullets, shields, (b, s) => { b.destroy(); s.destroy(); });
    this.physics.add.overlap(enemyBullets, player, (b, p) => { b.destroy(); damage(this); });

    // Enemy shooting timer
    this.time.addEvent({ delay: 900, loop: true, callback: () => enemyShoot(this) });
  }

  function addScore(v) {
    const s = parseInt(scoreText.getData('score') || 0) + v;
    scoreText.setData('score', s);
    scoreText.setText('Score: ' + s);
  }

  function damage(scene) {
    if (gameOver) return;
    player.lives -= 1;
    livesText.setText('Lives: ' + player.lives);
    player.setTint(0xff6b6b);
    scene.time.delayedCall(150, () => player.clearTint());
    if (player.lives <= 0) {
      endGame(scene, false);
    }
  }

  function enemyShoot(scene) {
    if (gameOver) return;
    const alive = invaders.getChildren();
    if (alive.length === 0) return;
    const shooter = Phaser.Utils.Array.GetRandom(alive);
    const b = enemyBullets.create(shooter.x, shooter.y + 10, 'ebullet');
    b.setVelocityY(260);
  }

  function endGame(scene, didWin) {
    gameOver = true; win = didWin;
    statusText.setText(didWin ? 'YOU WIN! 🎉' : 'GAME OVER 💥');
    scene.physics.pause();
    scene.time.delayedCall(1200, () => scene.scene.restart());
  }

  function checkWin(scene) {
    if (invaders.countActive(true) === 0) {
      endGame(scene, true);
    }
  }

  function update(time, delta) {
    if (gameOver) return;

    // Player move
    if (cursors.left.isDown) {
      player.setVelocityX(-280);
    } else if (cursors.right.isDown) {
      player.setVelocityX(280);
    } else {
      player.setVelocityX(0);
    }

    // Shoot
    if (Phaser.Input.Keyboard.JustDown(shootKey) && time - lastShot > shotCooldown) {
      lastShot = time;
      const b = bullets.create(player.x, player.y - 20, 'pbullet');
      b.setVelocityY(-520);
    }

    // Move invaders horizontally
    const dx = dir * invaderSpeed * (delta/1000);
    let touchedEdge = false;
    invaders.children.iterate(inv => {
      if (!inv) return;
      inv.x += dx;
      if (inv.x > W - 20 || inv.x < 20) touchedEdge = true;
    });
    if (touchedEdge) {
      dir *= -1;
      invaders.children.iterate(inv => { if (inv) inv.y += 18; });
      invaderSpeed = Math.min(invaderSpeed + 8, 180); // speed up a bit
    }

    // Lose if invaders reach player line
    let reached = false;
    invaders.children.iterate(inv => { if (inv && inv.y > player.y - 40) reached = true; });
    if (reached) endGame(this, false);

    // Cleanup off-screen bullets
    bullets.children.iterate(b => { if (b && b.y < -10) b.destroy(); });
    enemyBullets.children.iterate(b => { if (b && b.y > H + 10) b.destroy(); });
  }

  new Phaser.Game(config);
})();
</script>
"""

st.components.v1.html(html, height=CANVAS_HEIGHT, scrolling=False)

st.divider()
st.write("Cuter pixel palette, bunkers, enemy fire, and auto-restart. Want mobile touch buttons or sounds next?")
```
