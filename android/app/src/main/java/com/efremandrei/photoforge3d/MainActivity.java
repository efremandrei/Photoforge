package com.efremandrei.photoforge3d;

import android.app.*;
import android.os.*;
import android.content.*;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.provider.MediaStore;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.net.*;
import java.util.*;
import java.util.concurrent.*;

public class MainActivity extends Activity {
    private static final int IMPORT=10,CAPTURE=11,SAVE=12;
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final ArrayList<Uri> photos=new ArrayList<>();
    private android.content.SharedPreferences prefs;
    private boolean dark,connected=false,busy=false,visible=false,previewLoaded=false;
    private int bg,fg,panel,muted;
    private String server="",token="",jobId="",jobStatus="";
    private Uri captureUri;
    private LinearLayout content,thumbs;
    private EditText address,code,name,size;
    private EditText[][] crop=new EditText[3][2];
    private TextView status,count,stats;
    private ProgressBar progress;
    private MeshView mesh;
    private CheckBox seal;
    private Button reconstruct,export;
    private final Runnable polling=new Runnable(){public void run(){if(visible&&!jobId.isEmpty()&&!busy)poll();if(visible)handler.postDelayed(this,2500);}};

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);prefs=getSharedPreferences("settings",MODE_PRIVATE);dark=prefs.getBoolean("dark",true);
        server=prefs.getString("server","");token=prefs.getString("token","");jobId=prefs.getString("job","");
        try { JSONArray stored=new JSONArray(prefs.getString("photos","[]"));for(int i=0;i<stored.length();i++)photos.add(Uri.parse(stored.getString(i))); } catch(Exception ignored){}
        if(b!=null&&b.containsKey("capture"))captureUri=Uri.parse(b.getString("capture"));
        build();
    }
    @Override protected void onStart(){super.onStart();visible=true;handler.removeCallbacks(polling);handler.post(polling);}
    @Override protected void onStop(){super.onStop();visible=false;handler.removeCallbacks(polling);}
    @Override protected void onSaveInstanceState(Bundle b){super.onSaveInstanceState(b);if(captureUri!=null)b.putString("capture",captureUri.toString());}
    private int dp(float n){return (int)(n*getResources().getDisplayMetrics().density+.5f);}
    private GradientDrawable shape(int color){GradientDrawable s=new GradientDrawable();s.setColor(color);s.setCornerRadius(dp(14));return s;}
    private TextView label(String text,int sp,int color){TextView t=new TextView(this);t.setText(text);t.setTextSize(sp);t.setTextColor(color);t.setPadding(0,dp(6),0,dp(6));return t;}
    private Button button(String text,Runnable action){Button b=new Button(this);b.setText(text);b.setAllCaps(false);b.setTextColor(fg);b.setTextSize(14);b.setBackgroundTintList(ColorStateList.valueOf(panel));b.setMinHeight(dp(48));b.setOnClickListener(v->action.run());return b;}
    private EditText input(String hint,String value,boolean number){EditText e=new EditText(this);e.setTextColor(fg);e.setHintTextColor(muted);e.setTextSize(15);e.setSingleLine(true);e.setHint(hint);e.setText(value);if(number)e.setInputType(8194);e.setPadding(dp(10),dp(10),dp(10),dp(10));return e;}
    private LinearLayout card(String title){LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);l.setPadding(dp(16),dp(10),dp(16),dp(16));l.setBackground(shape(panel));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.bottomMargin=dp(14);content.addView(l,p);l.addView(label(title,12,0xff36c8b2));return l;}
    private void row(LinearLayout parent,View a,View b){LinearLayout r=new LinearLayout(this);r.setOrientation(LinearLayout.HORIZONTAL);r.addView(a,new LinearLayout.LayoutParams(0,-2,1));r.addView(b,new LinearLayout.LayoutParams(0,-2,1));parent.addView(r);}
    private void build(){
        bg=dark?0xff101722:0xffedf3fa;fg=dark?0xffecf4fa:0xff192433;panel=dark?0xff1c2838:Color.WHITE;muted=dark?0xffacbdcd:0xff52667a;
        getWindow().setStatusBarColor(bg);getWindow().setNavigationBarColor(bg);
        LinearLayout outer=new LinearLayout(this);outer.setOrientation(LinearLayout.VERTICAL);outer.setBackgroundColor(bg);
        outer.setOnApplyWindowInsetsListener((v,insets)->{v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());return insets.consumeSystemWindowInsets();});
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);outer.addView(scroll,new LinearLayout.LayoutParams(-1,-1));
        content=new LinearLayout(this);content.setOrientation(LinearLayout.VERTICAL);content.setPadding(dp(18),dp(16),dp(18),dp(24));scroll.addView(content);
        LinearLayout header=new LinearLayout(this);header.setGravity(Gravity.CENTER_VERTICAL);
        TextView title=label("◈ PhotoForge3D",23,fg);header.addView(title,new LinearLayout.LayoutParams(0,-2,1));
        header.addView(button(dark?"☀":"☾",()->{dark=!dark;prefs.edit().putBoolean("dark",dark).apply();previewLoaded=false;build();}));content.addView(header);
        content.addView(label("PHOTOS → GEOMETRY → PRINT",11,0xff36c8b2));
        content.addView(label("Capture every angle. Rebuild a real surface.\nSet the size and take it to your slicer.",15,muted));
        LinearLayout pc=card("01   CONNECT YOUR PC");
        address=input("PC address · http://192.168.x.x:8765",server,false);pc.addView(address);
        code=input("Pairing code shown on PC",token,false);code.setInputType(129);pc.addView(code);
        row(pc,button("Connect",this::connect),button("Capture guide",this::guide));
        pc.addView(label("Open the PC app → Connect Android phone.\nUse the same trusted Wi-Fi; keep the PC app open.",12,muted));
        LinearLayout capture=card("02   CAPTURE YOUR OBJECT");
        name=input("Object name",prefs.getString("name","My object"),false);capture.addView(name);
        row(capture,button("Take photo",this::capture),button("Import photos",this::pick));
        count=label("",14,fg);capture.addView(count);
        HorizontalScrollView gallery=new HorizontalScrollView(this);thumbs=new LinearLayout(this);gallery.addView(thumbs);capture.addView(gallery);
        row(capture,button("Remove last",()->{if(!photos.isEmpty())photos.remove(photos.size()-1);savePhotos();updatePhotos();}),button("Clear selection",()->{photos.clear();savePhotos();updatePhotos();}));
        capture.addView(label("Aim for 30–80 overlapping photos around a stationary object, at several heights. Include the top and bottom. Shiny or clear objects are difficult.",13,muted));
        reconstruct=button("Reconstruct on PC →",this::upload);capture.addView(reconstruct);
        LinearLayout result=card("03   INSPECT & EXPORT");
        status=label(jobId.isEmpty()?"Connect to your PC to begin.":"Restoring scan status…",14,fg);result.addView(status);
        progress=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);progress.setProgressTintList(ColorStateList.valueOf(0xff36c8b2));result.addView(progress);
        mesh=new MeshView(this);mesh.theme(dark);result.addView(mesh,new LinearLayout.LayoutParams(-1,dp(245)));
        result.addView(label("Drag to rotate · axes: X red, Y green, Z blue",12,muted));
        stats=label("",13,muted);result.addView(stats);
        row(result,button("Previous scans",this::scans),button("Cancel scan",this::cancel));
        result.addView(label("Crop background · model-axis ranges (0–100%)",13,fg));
        for(int i=0;i<3;i++){LinearLayout r=new LinearLayout(this);r.addView(label("XYZ".substring(i,i+1)+"  ",16,fg));for(int j=0;j<2;j++){crop[i][j]=input(j==0?"Min %":"Max %",j==0?"0":"100",true);r.addView(crop[i][j],new LinearLayout.LayoutParams(0,-2,1));}result.addView(r);}
        result.addView(label("Longest dimension (mm)",14,fg));size=input("1–2000 mm","100",true);result.addView(size);
        seal=new CheckBox(this);seal.setText("Seal gaps (may change / thicken geometry)");seal.setTextColor(fg);seal.setButtonTintList(ColorStateList.valueOf(0xff36c8b2));result.addView(seal);
        export=button("Prepare & save STL →",this::export);result.addView(export);
        result.addView(label("Photos alone do not establish scale. Inspect the cropped model, set its size, then check the STL and supports in your slicer.",12,muted));
        content.addView(button("About PhotoForge3D",this::about));setContentView(outer);outer.requestApplyInsets();updatePhotos();
    }
    private void info(String title,String text){new AlertDialog.Builder(this).setTitle(title).setMessage(text).setPositiveButton("OK",null).show();}
    private void error(Exception e){String s=e.getMessage();runOnUiThread(()->info("PhotoForge3D",s==null?"The operation failed. Please retry.":s));}
    private void guide(){info("Capture guide","Keep the object still and walk the camera around it.\n\nTake 30–80 sharp photos in 2–3 rings at different heights, with 70–80% overlap. Keep the same lens, avoid zoom, and use soft, even light.\n\nCapture every side you need. A turntable with an unmasked stationary background can confuse reconstruction. Matte, textured objects work best. Glossy, clear, plain, or moving objects often fail.\n\nCPU processing can take minutes to hours. Cropping and gap sealing may change the model; inspect the result in your slicer.");}
    private void about(){info("About PhotoForge3D","Version 1.0.0 · build 1\nAndrei Efremuahkin\nandrei.efr@gmail.com\nhttps://github.com/efremandrei/Photoforge\n\nLocal photogrammetry with COLMAP (BSD) and OpenMVS (AGPL-3.0). STL checks confirm a closed solid, not guaranteed dimensional accuracy or printability.");}
    private String validateAddress(String s) throws Exception{
        URI uri=new URI(s);if(!"http".equals(uri.getScheme())||uri.getHost()==null||uri.getUserInfo()!=null||uri.getQuery()!=null||uri.getFragment()!=null||!(uri.getPath()==null||uri.getPath().isEmpty()||uri.getPath().equals("/")))throw new Exception("Enter the PC's local HTTP address, including :8765.");
        InetAddress ip=InetAddress.getByName(uri.getHost());if(!(ip.isSiteLocalAddress()||ip.isLoopbackAddress()))throw new Exception("Use a local PC address on your trusted Wi-Fi.");return s.replaceAll("/+$","");
    }
    private HttpURLConnection connection(String path,String method) throws Exception{
        if(server.isEmpty()||token.isEmpty())throw new Exception("Connect to your PC with its address and pairing code first.");
        HttpURLConnection c=(HttpURLConnection)new URL(server+path).openConnection();c.setInstanceFollowRedirects(false);c.setRequestMethod(method);c.setConnectTimeout(10000);c.setReadTimeout(180000);c.setRequestProperty("X-Pairing-Token",token);return c;
    }
    private String response(HttpURLConnection c) throws Exception{
        int rc=c.getResponseCode();InputStream stream=rc<400?c.getInputStream():c.getErrorStream();String text="";
        if(stream!=null)try(InputStream in=stream;ByteArrayOutputStream out=new ByteArrayOutputStream()){copy(in,out);text=out.toString("UTF-8");}
        if(rc<200||rc>=300){String detail=text;try{detail=new JSONObject(text).optString("detail",text);}catch(Exception ignored){}throw new Exception(detail.isEmpty()?"PC returned HTTP "+rc:detail);}return text;
    }
    private String request(String path,String method,JSONObject body) throws Exception{
        HttpURLConnection c=connection(path,method);try{if(body!=null){c.setDoOutput(true);c.setRequestProperty("Content-Type","application/json");try(OutputStream out=c.getOutputStream()){out.write(body.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));}}return response(c);}finally{c.disconnect();}
    }
    private void connect(){
        String a=address.getText().toString().trim(),t=code.getText().toString().trim();status.setText("Connecting…");
        worker.execute(()->{try{String checked=validateAddress(a);server=checked;token=t;request("/jobs","GET",null);connected=true;prefs.edit().putString("server",server).putString("token",token).apply();runOnUiThread(()->status.setText("PC connected. Import or take photos to begin."));}catch(Exception e){connected=false;error(e);}});
    }
    private void savePhotos(){JSONArray a=new JSONArray();for(Uri u:photos)a.put(u.toString());prefs.edit().putString("photos",a.toString()).apply();}
    private void updatePhotos(){count.setText(photos.size()+" photos selected");thumbs.removeAllViews();int start=Math.max(0,photos.size()-12);for(int i=start;i<photos.size();i++){ImageView image=new ImageView(this);image.setScaleType(ImageView.ScaleType.CENTER_CROP);image.setContentDescription("Selected photo "+(i+1));thumbs.addView(image,new LinearLayout.LayoutParams(dp(60),dp(60)));Uri uri=photos.get(i);worker.execute(()->{try{android.graphics.Bitmap thumb=getContentResolver().loadThumbnail(uri,new android.util.Size(120,120),null);runOnUiThread(()->image.setImageBitmap(thumb));}catch(Exception ignored){}});}}
    private void pick(){Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.setType("image/*");i.addCategory(Intent.CATEGORY_OPENABLE);i.putExtra(Intent.EXTRA_ALLOW_MULTIPLE,true);startActivityForResult(i,IMPORT);}
    private void capture(){try{Intent i=new Intent(MediaStore.ACTION_IMAGE_CAPTURE);if(i.resolveActivity(getPackageManager())==null)throw new Exception("No camera app is available. Import photos instead.");ContentValues v=new ContentValues();v.put(MediaStore.Images.Media.DISPLAY_NAME,"PhotoForge3D-"+System.currentTimeMillis()+".jpg");v.put(MediaStore.Images.Media.MIME_TYPE,"image/jpeg");v.put(MediaStore.Images.Media.RELATIVE_PATH,"Pictures/PhotoForge3D");v.put(MediaStore.Images.Media.IS_PENDING,1);captureUri=getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI,v);if(captureUri==null)throw new Exception("Could not create the photo.");i.putExtra(MediaStore.EXTRA_OUTPUT,captureUri);i.setClipData(ClipData.newRawUri("Capture",captureUri));i.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivityForResult(i,CAPTURE);}catch(Exception e){error(e);}}
    @Override protected void onActivityResult(int req,int result,Intent data){super.onActivityResult(req,result,data);if(req==CAPTURE&&captureUri!=null){Uri u=captureUri;captureUri=null;try{if(result==RESULT_OK){ContentValues v=new ContentValues();v.put(MediaStore.Images.Media.IS_PENDING,0);getContentResolver().update(u,v,null,null);photos.add(u);}else getContentResolver().delete(u,null,null);}catch(Exception e){error(e);}savePhotos();updatePhotos();return;}
        if(result!=RESULT_OK||data==null)return;
        if(req==IMPORT){ArrayList<Uri> list=new ArrayList<>();if(data.getClipData()!=null)for(int i=0;i<data.getClipData().getItemCount();i++)list.add(data.getClipData().getItemAt(i).getUri());else if(data.getData()!=null)list.add(data.getData());for(Uri u:list){if(photos.size()>=240)break;try{getContentResolver().takePersistableUriPermission(u,Intent.FLAG_GRANT_READ_URI_PERMISSION);}catch(Exception ignored){}if(!photos.contains(u))photos.add(u);}savePhotos();updatePhotos();}
        if(req==SAVE&&data.getData()!=null){Uri dest=data.getData();worker.execute(()->{try(InputStream in=new FileInputStream(new File(getCacheDir(),"model.stl"));OutputStream out=getContentResolver().openOutputStream(dest)){if(out==null)throw new IOException("Cannot write to selected location.");copy(in,out);runOnUiThread(()->info("STL saved","Your model was saved. Open it in a slicer to inspect size, orientation and supports."));}catch(Exception e){error(e);}});}
    }
    private void upload(){
        if(busy)return;if(photos.size()<8){info("More angles needed","Choose at least 8 distinct photos; aim for 30–80 for an object.");return;}
        if(server.isEmpty()||token.isEmpty()){info("Connect your PC","Enter the PC address and pairing code, then tap Connect.");return;}
        busy=true;reconstruct.setEnabled(false);status.setText("Uploading photos to your PC…");ArrayList<Uri> selected=new ArrayList<>(photos);String objectName=name.getText().toString();prefs.edit().putString("name",objectName).apply();
        worker.execute(()->{HttpURLConnection c=null;try{
            c=connection("/jobs","POST");String boundary="PhotoForge"+UUID.randomUUID();c.setDoOutput(true);c.setChunkedStreamingMode(1024*1024);c.setRequestProperty("Content-Type","multipart/form-data; boundary="+boundary);
            try(OutputStream out=new BufferedOutputStream(c.getOutputStream())){
                write(out,"--"+boundary+"\r\nContent-Disposition: form-data; name=\"name\"\r\n\r\n"+objectName.replace("\r","").replace("\n","")+"\r\n");int i=0;for(Uri uri:selected){write(out,"--"+boundary+"\r\nContent-Disposition: form-data; name=\"images\"; filename=\"photo"+(i++)+".jpg\"\r\nContent-Type: application/octet-stream\r\n\r\n");try(InputStream in=getContentResolver().openInputStream(uri)){if(in==null)throw new IOException("A selected photo is unavailable. Import it again.");copy(in,out);}write(out,"\r\n");}write(out,"--"+boundary+"--\r\n");
            }
            JSONObject d=new JSONObject(response(c));jobId=d.getString("id");prefs.edit().putString("job",jobId).apply();previewLoaded=false;runOnUiThread(()->{mesh.clear();status.setText("Photos uploaded. Reconstruction is running on your PC.");});
        }catch(Exception e){error(e);}finally{if(c!=null)c.disconnect();busy=false;runOnUiThread(()->reconstruct.setEnabled(true));}});
    }
    private void write(OutputStream out,String s)throws IOException{out.write(s.getBytes(java.nio.charset.StandardCharsets.UTF_8));}
    private void copy(InputStream in,OutputStream out)throws IOException{byte[] buffer=new byte[65536];int n;while((n=in.read(buffer))!=-1)out.write(buffer,0,n);}
    private void poll(){if(jobId.isEmpty())return;String selected=jobId;worker.execute(()->{try{JSONObject d=new JSONObject(request("/jobs/"+selected,"GET",null));if(!selected.equals(jobId))return;jobStatus=d.getString("status");String text=d.getString("message");int pct=d.optInt("progress",0);runOnUiThread(()->{status.setText(text);progress.setProgress(pct);});if(jobStatus.equals("complete")&&!previewLoaded){JSONObject p=new JSONObject(request("/jobs/"+selected+"/preview","GET",null));JSONArray triangles=p.getJSONArray("triangles");JSONObject s=p.getJSONObject("stats");previewLoaded=true;runOnUiThread(()->{try{mesh.mesh(triangles);stats.setText(s.getInt("triangles")+" surface triangles · "+(s.getBoolean("watertight")?"closed surface":"open surface; missing sides need capture or repair"));}catch(Exception e){error(e);}});}}catch(Exception e){runOnUiThread(()->status.setText("PC unavailable. Keep the PC app open and reconnect to its Wi-Fi."));}});}
    private void scans(){worker.execute(()->{try{JSONArray list=new JSONArray(request("/jobs","GET",null));String[] labels=new String[list.length()];for(int i=0;i<labels.length;i++)labels[i]=list.getJSONObject(i).getString("name")+" · "+list.getJSONObject(i).getString("status");runOnUiThread(()->new AlertDialog.Builder(this).setTitle("Scans on your PC").setItems(labels,(dialog,which)->{try{jobId=list.getJSONObject(which).getString("id");prefs.edit().putString("job",jobId).apply();previewLoaded=false;mesh.clear();poll();}catch(Exception e){error(e);}}).setNegativeButton("Close",null).show());}catch(Exception e){error(e);}});}
    private void cancel(){if(jobId.isEmpty())return;worker.execute(()->{try{request("/jobs/"+jobId+"/cancel","POST",null);poll();}catch(Exception e){error(e);}});}
    private void export(){
        if(busy)return;if(!jobStatus.equals("complete")){info("Surface needed","Select a completed scan before exporting.");return;}
        JSONObject options=new JSONObject();try{double mm=Double.parseDouble(size.getText().toString());if(!Double.isFinite(mm)||mm<1||mm>2000)throw new Exception("Enter a size between 1 and 2000 mm.");options.put("longest_mm",mm);options.put("solidify",seal.isChecked());JSONArray ranges=new JSONArray();for(int i=0;i<3;i++){double a=Double.parseDouble(crop[i][0].getText().toString())/100,b=Double.parseDouble(crop[i][1].getText().toString())/100;if(!Double.isFinite(a)||!Double.isFinite(b)||a<0||b>1||a>=b)throw new Exception("Crop ranges must satisfy 0 ≤ minimum < maximum ≤ 100%.");ranges.put(new JSONArray().put(a).put(b));}options.put("crop",ranges);}catch(Exception e){error(e);return;}
        busy=true;export.setEnabled(false);status.setText("Preparing and verifying your STL…");String selected=jobId;
        worker.execute(()->{try{
            JSONObject report=new JSONObject(request("/jobs/"+selected+"/export","POST",options));HttpURLConnection c=connection("/jobs/"+selected+"/model.stl","GET");try{if(c.getResponseCode()!=200)throw new IOException("Could not download the STL.");try(InputStream in=c.getInputStream();OutputStream out=new FileOutputStream(new File(getCacheDir(),"model.stl"))){copy(in,out);}}finally{c.disconnect();}
            JSONArray dims=report.getJSONArray("dimensions");String text=String.format(Locale.US,"Closed solid · %.2f × %.2f × %.2f mm\n%s",dims.getDouble(0),dims.getDouble(1),dims.getDouble(2),report.getString("warning"));runOnUiThread(()->{status.setText(text);Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT);i.setType("application/octet-stream");i.addCategory(Intent.CATEGORY_OPENABLE);i.putExtra(Intent.EXTRA_TITLE,"PhotoForge3D-model.stl");startActivityForResult(i,SAVE);});
        }catch(Exception e){error(e);}finally{busy=false;runOnUiThread(()->export.setEnabled(true));}});
    }
}


