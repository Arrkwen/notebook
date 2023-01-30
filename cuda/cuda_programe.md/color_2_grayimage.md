```cuda

__global__ void color_2_grayimage(const uchar* d_colorimage, uchar* d_grayimage, const int rows, cont int cols){
	// 2D维度
	int col = threadIdx.x+threadIdx.x*blockDim.x;
	int row = threadIdx.y+threadIdx.y*blockDim.y;
	if(rol<cols&&row<rows){
		int cur_index = col*rows+col;
		int offset = cur_index*4;
		uchar* cur_color_ptr = d_colorimage[idx*4];
		uchar R = cur_color_ptr[0];
		uchar G = cur_color_ptr[1];
		uchar B = cur_color_ptr[2];
		uchar a = cur_color_ptr[3];

		char d_grayimage[idx] = 0.299*R+0.587*G+0.114*B;
	}
}

```
