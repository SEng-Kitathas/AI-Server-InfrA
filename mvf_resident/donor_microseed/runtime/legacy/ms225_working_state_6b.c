#include <stdint.h>
#include <stddef.h>
typedef struct { uint8_t src[2]; uint8_t hi[2][2]; } ms_ws;
static uint16_t total(const ms_ws *s, int j){ return (uint16_t)s->hi[j][0]+s->hi[j][1]; }
void ms_ws_init(ms_ws *s){ s->src[0]=255; s->src[1]=255; s->hi[0][0]=s->hi[0][1]=s->hi[1][0]=s->hi[1][1]=0; }
static void ins(ms_ws *s,int j,uint8_t v){ if(v>s->hi[j][0]){s->hi[j][1]=s->hi[j][0];s->hi[j][0]=v;} else if(v>s->hi[j][1]) s->hi[j][1]=v; }
void ms_ws_update(ms_ws *s,uint8_t src,uint8_t score){
  if(s->src[0]==src){ins(s,0,score);return;} if(s->src[1]==src){ins(s,1,score);return;}
  if(s->src[0]==255){s->src[0]=src;ins(s,0,score);return;} if(s->src[1]==255){s->src[1]=src;ins(s,1,score);return;}
  uint16_t t0=total(s,0),t1=total(s,1); int loser=(t0<t1 || (t0==t1 && s->src[0]>s->src[1]))?0:1;
  uint16_t lt=total(s,loser);
  if((uint16_t)score>lt || ((uint16_t)score==lt && src<s->src[loser])){s->src[loser]=src;s->hi[loser][0]=score;s->hi[loser][1]=0;}
}
uint8_t ms_ws_best(const ms_ws *s){ uint16_t a=total(s,0),b=total(s,1); if(s->src[1]==255)return s->src[0]; if(a>b)return s->src[0]; if(b>a)return s->src[1]; return s->src[0]<s->src[1]?s->src[0]:s->src[1]; }
size_t ms_ws_size(void){return sizeof(ms_ws);}
