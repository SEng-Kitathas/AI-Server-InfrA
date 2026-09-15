/* Microseed tiny core v0.1: freestanding candidate; no heap, no libc calls. */
typedef unsigned char u8; typedef signed char i8; typedef unsigned short u16; typedef signed short i16; typedef unsigned long u32;
typedef char assert_u8[(sizeof(u8)==1)?1:-1]; typedef char assert_i16[(sizeof(i16)==2)?1:-1];
enum {MS_OK=0,MS_UNKNOWN_TASK=1,MS_UNKNOWN_REGIME=2,MS_UNKNOWN_UNQUALIFIED=3,MS_UNKNOWN_LENGTH=4,MS_CORRUPT_MODEL=5};
enum {TASK_CIRCLE=0,TASK_CROSS=1,TASK_XOR=2,TASK_SEQUENCE=3};
static const u8 CIRCLE_MODEL[37]={8,129,32,1,10,18,130,64,32,66,128,170,132,160,6,34,8,8,2,10,8,42,34,168,40,136,2,160,8,130,170,0,170,34,162,162,255};
static const u8 SEQ_IDS[12]={2,5,12,13,14,15,18,60,76,77,79,80};
static const i8 SEQ_W[12]={57,23,-51,-55,-54,-54,5,-8,-7,-5,-6,46};
static const i8 SEQ_BIAS=-51;
static int iabs_i(int x){return x<0?-x:x;} static int trit(int v){return (v>0)-(v<0);}
static void xy9(int x,int y,i8 e[9]){int ax=iabs_i(x),ay=iabs_i(y);e[0]=(i8)trit(x);e[1]=(i8)trit(y);e[2]=(i8)trit(x*y);e[3]=(i8)trit(ax-4);e[4]=(i8)trit(ay-4);e[5]=(i8)trit(x*x+y*y-32);e[6]=(i8)trit(4-iabs_i(x-y));e[7]=(i8)trit(4-iabs_i(x+y));e[8]=(i8)trit(ax-ay);}
static int unpack_trit(const u8 *b,int idx){int c=(b[idx>>2]>>(2*(idx&3)))&3;return c==0?-1:(c==1?0:(c==2?1:99));}
static int circle_infer(int x,int y,int *score){i8 e[9];int lab,p,j,s,best[2];xy9(x,y,e);for(lab=0;lab<2;lab++){best[lab]=-32767;for(p=0;p<8;p++){s=0;for(j=0;j<9;j++)s+=e[j]*unpack_trit(CIRCLE_MODEL,(lab*8+p)*9+j);if(s>best[lab])best[lab]=s;}}*score=best[1]-best[0]+(i8)CIRCLE_MODEL[36];return *score>=0;}
static int cross_infer(int x,int y,int *score){i8 e[9];xy9(x,y,e);*score=4-e[5]+8*e[6]+7*e[7];return *score>=0;}static int xor_infer(int x,int y,int *score){i8 e[9];xy9(x,y,e);*score=-2-6*e[2]-2*e[6];return *score>=0;}
int ms_geometry(int task,int x,int y,u8 qualified_mask,int *label,int *score){if(task<0||task>2)return MS_UNKNOWN_TASK;if(x==0||y==0||x>12||x<-12||y>12||y<-12)return MS_UNKNOWN_REGIME;if(!(qualified_mask&(1u<<task)))return MS_UNKNOWN_UNQUALIFIED;if(task==0)*label=circle_infer(x,y,score);else if(task==1)*label=cross_infer(x,y,score);else *label=xor_infer(x,y,score);return MS_OK;}
/* 3-byte sequence latent state: score little-endian + packed len/previous symbols. Declared max length=12. */
static i16 st_score(const u8 st[3]){u16 u=(u16)st[0]|((u16)st[1]<<8);return (i16)u;} static void st_set_score(u8 st[3],i16 v){u16 u=(u16)v;st[0]=(u8)(u&255);st[1]=(u8)(u>>8);}
void ms_seq_init(u8 st[3]){st_set_score(st,(i16)SEQ_BIAS);st[2]=0;}
static int seq_w_for(int fid){int i;for(i=0;i<12;i++)if(SEQ_IDS[i]==fid)return SEQ_W[i];return 0;}
int ms_seq_push(u8 st[3],u8 symbol){int len=(st[2]>>4)&15,p1=st[2]&3,p2=(st[2]>>2)&3,sc;if(symbol>3)return MS_UNKNOWN_TASK;if(len>=12)return MS_UNKNOWN_LENGTH;sc=st_score(st);sc+=seq_w_for(symbol);if(len>=1)sc+=seq_w_for(4+p1*4+symbol);if(len>=2)sc+=seq_w_for(20+p2*16+p1*4+symbol);len++;st_set_score(st,(i16)sc);st[2]=(u8)((len<<4)|((p1&3)<<2)|(symbol&3));return MS_OK;}
int ms_seq_project(const u8 st[3],int *label,int *score){*score=(int)st_score(st);*label=*score>=0;return MS_OK;}
static u16 crc16_update(u16 c,u8 b){int i;c^=(u16)b<<8;for(i=0;i<8;i++)c=(c&0x8000)?(u16)((c<<1)^0x1021):(u16)(c<<1);return c;}
u16 ms_geometry_crc16(void){u16 c=0xffff;int i;for(i=0;i<37;i++)c=crc16_update(c,CIRCLE_MODEL[i]);return c;}
int ms_geometry_crc_ok(void){return ms_geometry_crc16()==4556;}
int ms_model_bytes(void){return 37+25;} int ms_seq_state_bytes(void){return 3;}
