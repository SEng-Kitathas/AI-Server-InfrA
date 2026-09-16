#include <stdint.h>
#define NC 11
typedef struct {uint16_t reqc, reqf, out;} Cap;
static const Cap C[NC]={{3,0,1},{5,0,1},{1,1,2},{8,0,4},{16,0,8},{32,0,16},{64,16,32},{128,0,64},{256,32,128},{0,34,256},{512,256,512}};
static int ensure(uint16_t f,uint16_t comps,uint16_t qual,uint16_t *have,uint16_t *plan,uint16_t visiting){
 if((*have)&f)return 1; if(visiting&f)return 0; visiting|=f;
 for(int i=0;i<NC;i++){ if(!(qual&(1u<<i))||C[i].out!=f)continue; if(C[i].reqc & ~comps)continue; uint16_t h=*have,p=*plan; int ok=1;
   for(int b=0;b<10;b++){uint16_t rf=1u<<b;if((C[i].reqf&rf)&&!ensure(rf,comps,qual,have,plan,visiting)){ok=0;break;}}
   if(ok){*have|=C[i].out;*plan|=1u<<i;return 1;} *have=h;*plan=p; } return 0;}
uint16_t ms_compose(uint8_t goals,uint16_t comps,uint16_t qual,uint8_t *ok){uint16_t have=0,plan=0; static const uint16_t gf[7]={2,4,8,32,64,128,512}; for(int g=0;g<7;g++)if(goals&(1u<<g))if(!ensure(gf[g],comps,qual,&have,&plan,0)){*ok=0;return 0;}*ok=1;return plan;}
