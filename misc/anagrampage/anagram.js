/* I think I wrote this at the "Ballmer peak". I don't remember it. It kind of works. --Rob */
var counts = new Array();
var total=0;

var freqs = [.08167, .01492, .02782, .04253, .12702, .02228,
.02015, .06094, .06966, .00153, .00772, .04025, .02406, .06749, .07507, .01929,
.00095, .05987, .06327, .09056, .02758, .00978, .02360, .00150, .01974, .00074];
var topwords = words.slice(0, 10000); // words must be loaded from 10000words.js

var width=780;
var height=350;
var baseline=300;
var stdHeight=30;

var timeout=null;

window.onload = function() {
    canvas = document.getElementById("canvas");
    context = canvas.getContext("2d");
    sourceElt = document.getElementById("sourcetext");
    anagramElt = document.getElementById("anagramtext");
    diffElt = document.getElementById("diff");
    suggestCommonElt = document.getElementById("suggest-common");

    canvas.width=width;
    canvas.height=height;
    context.textBaseline='top';
    context.font = "bold 14px monospace";
}

function update() {
  var sourcetext = sourceElt.value;
  var anagramtext = anagramElt.value;
  for (var letterIndex=0; letterIndex < 26; letterIndex++) {
    counts[letterIndex] = 0;
  }
  total=0;
  diffElt.value = "";
  for (var sourceIndex=0; sourceIndex < sourcetext.length; sourceIndex++) {
    var ccode = sourcetext.charCodeAt(sourceIndex);
    if (ccode >= 65 && ccode <= 90) {
      counts[ccode-65]++;
    }
    else if (ccode >= 97 && ccode <= 122) {
      counts[ccode-97]++;
    }
  }
  for (var anagramIndex=0; anagramIndex < anagramtext.length; anagramIndex++) {
    var ccode = anagramtext.charCodeAt(anagramIndex);
    if (ccode >= 65 && ccode <= 90) {
      counts[ccode-65]--;
    }
    else if (ccode >= 97 && ccode <= 122) {
      counts[ccode-97]--;
    }
  }

  for (var letterIndex=0; letterIndex < 26; letterIndex++) {
    total += Math.abs(counts[letterIndex]);
    for (var i=0; i < counts[letterIndex]; i++) {
      diffElt.value += String.fromCharCode(97+letterIndex);
    }
    for (var i=0; i < -counts[letterIndex]; i++) {
      diffElt.value += String.fromCharCode(65+letterIndex);
    }
  }
  
  updateCanvas();
  updateTimer();
}

function updateCanvas() {
  context.clearRect(0, 0, width, height);

  if (total == 0) {
    context.fillStyle="#0a0";
    context.fillText("Anagrammed!", 5, 5);
  }
  else {
    // draw the basic grid
    context.moveTo(0, baseline-0.5);
    context.lineTo(width, baseline-0.5);
    context.moveTo(0, baseline-stdHeight-0.5);
    context.lineTo(width, baseline-stdHeight-0.5);
    context.strokeStyle = "#ccc";
    context.stroke();

    for (var letterIndex=0; letterIndex < 26; letterIndex++) {
      var expected = freqs[letterIndex] * total;
      var increment = 1/expected;
      var actual = counts[letterIndex];
      var widthOffset = 0;
      context.fillStyle = "#048";
      if (increment * actual < 0.5) {
        context.fillStyle = "#a80";
      }
      if (actual == 0) {
        context.fillStyle = "#aaa";
      }
      if (actual < 0) {
        actual = -actual;
        context.fillStyle = "#a00";
        widthOffset = 5;
      }
      var barHeight = increment*stdHeight;
      for (var bar=0; bar < actual; bar++) {
        context.fillRect(letterIndex*30+widthOffset, baseline-(bar+1)*barHeight,
                         25-widthOffset*2, barHeight-Math.min(1, barHeight/2));
      }
      context.fillText(String.fromCharCode(97+letterIndex),
                       letterIndex*30+8, baseline+5);
    }
  }
}

function updateTimer() {
  if (timeout) window.clearTimeout(timeout);
  timeout = window.setTimeout(recommend, 500);
}

function recommend() {
  var suggestions = [];
  var suggestText = "";
  for (wordIdx in topwords) {
    word = topwords[wordIdx];
    var counts2 = counts.slice(0);
    var good=true;
    for (var wordIndex=0, end=word.length; wordIndex < end; wordIndex++) {
      var ccode = word.charCodeAt(wordIndex);
      if (ccode >= 65 && ccode <= 90) {
        counts2[ccode-65]--;
        if (counts2[ccode-65] < 0) {
          good=false;
          break;
        }
      }
      else if (ccode >= 97 && ccode <= 122) {
        counts2[ccode-97]--;
        if (counts2[ccode-97] < 0) {
          good=false;
        }
      }
    }
    if (good) {
      var goodness = letterGoodness(counts, counts2);
      var wordGoodness = goodness / (1000 + wordIdx);
      suggestions.push([word, wordGoodness])
    };
  }
  suggestions.sort(function (a, b) { return b[1] - a[1] });
  for (var i=0; i<20; i++) {
    if (suggestions[i]) {
      suggestText += ' '+suggestions[i][0];
    }
  }
  suggestCommonElt.textContent = suggestText;
}

function letterGoodness(counts, counts2) {
  var score = 0;
  var remain = 0;
  for (var i=0; i<26; i++) {
    remain += counts2[i];
  }
  if (remain == 0) return 1000000;
  for (var i=0; i<26; i++) {
    prop = counts2[i] / remain;
    score += Math.pow((1 - prop/freqs[i]), 4);
  }
  return 1.0 / (score + 0.0001) / remain;
}
