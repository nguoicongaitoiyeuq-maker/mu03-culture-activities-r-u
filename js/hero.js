function setHero() {
  const next = (slideIndex + 1) % slides.length;
  const front = slideFront ? document.getElementById('slideA') : document.getElementById('slideB');
  const back = slideFront ? document.getElementById('slideB') : document.getElementById('slideA');
  back.style.backgroundImage = `url("/asset/${slides[next]}")`;
  back.classList.add('active');
  front.classList.remove('active');
  slideFront = !slideFront;
  slideIndex = next;
}

document.getElementById('slideA').style.backgroundImage = 'url("/asset/1.jpg")';
setInterval(setHero, 6500);
