#include <stdint.h>
#pragma pack(push,1)
typedef struct { uint8_t cur; uint8_t depth; uint8_t hist[9]; } ms_intent_state;
#pragma pack(pop)
enum { EV_NOOP=0, EV_UNDO=1, EV_REJECT=2, EV_SET=3, EV_RESET=4 };
void ms_init(ms_intent_state* s){ s->cur=(0u<<0)|(1u<<2)|(0u<<4)|(2u<<6); s->depth=0; for(int i=0;i<9;i++)s->hist[i]=0; }
static uint8_t mask_for(uint8_t slot){ return (uint8_t)(3u<<(slot*2u)); }
static uint8_t default_val(uint8_t slot){ static const uint8_t d[4]={0,1,0,2}; return d[slot&3u]; }
int ms_apply(ms_intent_state* s,uint8_t kind,uint8_t slot,uint8_t val){
 if(kind==EV_NOOP||kind==EV_REJECT) return 0;
 if(kind==EV_UNDO){ if(s->depth){ s->cur=s->hist[--s->depth]; } return 0; }
 if(slot>3) return -1;
 if(kind==EV_SET||kind==EV_RESET){ if(s->depth>=9) return -2; s->hist[s->depth++]=s->cur; uint8_t v=(kind==EV_RESET)?default_val(slot):val; uint8_t m=mask_for(slot); s->cur=(uint8_t)((s->cur&~m)|((v&3u)<<(slot*2u))); return 0; }
 return -3;
}
uint8_t ms_cur(const ms_intent_state* s){return s->cur;} uint8_t ms_depth(const ms_intent_state* s){return s->depth;} int ms_size(void){return (int)sizeof(ms_intent_state);} 
