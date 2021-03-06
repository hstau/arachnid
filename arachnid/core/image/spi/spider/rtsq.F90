C -*-fortran-*-
C++*********************************************************************
C
C RTSQ.F     BUFOUT RETURN ADDED, SPEEDED UP      12/28/06 ArDean Leith
C            MERGED WITH ROT2QS_DL                 1/12/11 ArDean Leith
C            ROT2QS_PAD ADDED                      8/12/11 ArDean Leith
C            ROT2QS_BACK ADDED                    10/05/11 ArDean Leith
C            RENAMED FROM: ROT2QS                 12/28/11 ArDean Leith
C            REMOVED LINE-BY-LINE OUTPUT           1/04/12 ArDean Leith
C            RYE1 BUG                              5/08/12 ArDean Leith
C
C **********************************************************************
C=*                                                                    *                            
C=* This file is part of:   SPIDER - Modular Image Processing System.  *                            
C=* SPIDER System Authors:  Joachim Frank & ArDean Leith               *                            
C=* Copyright 1985-2012  Health Research Inc.,                         *                            
C=* Riverview Center, 150 Broadway, Suite 560, Menands, NY 12204.      *                            
C=* Email: spider@wadsworth.org                                        *                            
C=*                                                                    *                            
C=* SPIDER is free software; you can redistribute it and/or            *                            
C=* modify it under the terms of the GNU General Public License as     *                            
C=* published by the Free Software Foundation; either version 2 of the *                            
C=* License, or (at your option) any later version.                    *                            
C=*                                                                    *                            
C=* SPIDER is distributed in the hope that it will be useful,          *                            
C=* but WITHOUT ANY WARRANTY; without even the implied warranty of     *                            
C=* merchantability or fitness for a particular purpose.  See the GNU  *                            
C=* General Public License for more details.                           *                            
C=* You should have received a copy of the GNU General Public License  *                            
C=* along with this program. If not, see <http://www.gnu.org/licenses> *
C=*                                                                    *
C--*********************************************************************
C
C RTSQ(XIMG,BUFOUT, NX,NY, NXP,NYP, THETA,SCLI,SHXI,SHYI,IRTFLG)
C
C PURPOSE: ROTATES AND SHIFTS A SLICE OF AN IMAGE, ROW BY ROW
C
C PARAMETERS: XIMG        INPUT IMAGE                        (INPUT)
C             BUFOUT      OUTPUT IMAGE OR LINE BUFFER        (OUTPUT)
C             NX,NY       INPUT IMAGE SIZE                   (INPUT)
C             NXP,NYP     OUTPUT IMAGE SIZE                  (INPUT)
C             THETA,SCLI  ROTATION AND SCALE                 (INPUT)
C             SHXI,SHYI   SHIFTS                             (INPUT)
C             USEBACK     USE BACKGROUND                     (INPUT)
C             BACK        BACKGROUND                         (INPUT)
C             IREC1       IMAGE STARTING RECORD              (INPUT)
C             LUN         LUN FOR OUTPUT (0 IS NO FILE OUT)  (INPUT)
C  
C--*********************************************************************

         SUBROUTINE RTSQ(XIMG,BUFOUT, NX,NY, NXP,NYP,
     &                     THETA,SCLI,SHXI,SHYI, IRTFLG)

         IMPLICIT NONE
         REAL            :: XIMG(NX,NY)
         INTEGER         :: NX,NY 
         REAL            :: BUFOUT(NXP,NYP)   
         INTEGER         :: NXP,NYP
         REAL            :: THETA,SCLI,SHXI,SHYI
         INTEGER         :: IRTFLG

	 REAL, PARAMETER :: QUADPI = 3.14159265358979323846
	 REAL, PARAMETER :: DGR_TO_RAD = (QUADPI/180)

         REAL            :: SHX,SHY,RY1,RX1,RY2,RX2,COD,SID,XI
         REAL            :: CODDSCLI,SIDDSCLI,FIXCENMSHX,FIYCENMSHY 
         REAL            :: RYE2,RYE1,RXE2,RXE1,YI
         REAL            :: YCOD,YSID,YOLD,XOLD
         INTEGER         :: IYCEN,IXCEN,IX,IY

         REAL            :: quadri

C        SHIFT WITHIN IMAGE BOUNDARY
         SHX   = AMOD(SHXI,FLOAT(NX))
         SHY   = AMOD(SHYI,FLOAT(NY))

C        SPIDER IMAGE CENTER
         IYCEN = NY/2+1
         IXCEN = NX/2+1

C        IMAGE DIMENSIONS AROUND ORIGIN
         RX1   = -NX/2
         RX2   =  NX/2
         RY1   = -NY/2
         RY2   =  NY/2

         IF (MOD(NX,2) == 0) THEN
            RX2  =  RX2 - 1.0
            RXE1 = -NX
            RXE2 =  NX
         ELSE
            RXE1 = -NX - 1
            RXE2 =  NX + 1
         ENDIF

         IF (MOD(NY,2) == 0) THEN
            RY2  =  RY2 - 1.0
            RYE1 = -NY 
            RYE2 =  NY
         ELSE
            RYE1 = -NY - 1
            RYE2 =  NY + 1
         ENDIF

C        CREATE TRANSFORMATION MATRIX
         COD = COS(THETA * DGR_TO_RAD)
         SID = SIN(THETA * DGR_TO_RAD)

C        ADJUST FOR SCALING
         CODDSCLI   = COD / SCLI
         SIDDSCLI   = SID / SCLI

C        -(CENTER PLUS SHIFT)
         FIXCENMSHX = -IXCEN - SHX
         FIYCENMSHY = -IYCEN - SHY

c$omp    parallel do private(iy,yi,ycod,ysid, ix,xi, xold,yold)
         DO IY=1,NY

            YI = IY + FIYCENMSHY
            IF (YI < RY1) YI = MIN(YI+RYE2, RY2)
            IF (YI > RY2) YI = MAX(YI+RYE1, RY1)

            YCOD =  YI * CODDSCLI + IYCEN
            YSID = -YI * SIDDSCLI + IXCEN

            DO IX=1,NX
               XI = IX + FIXCENMSHX                           
               IF (XI  <  RX1) XI = MIN(XI+RXE2, RX2)   
               IF (XI  >  RX2) XI = MAX(XI+RXE1, RX1) 
 
               YOLD          = XI * SIDDSCLI + YCOD  
               XOLD          = XI * CODDSCLI + YSID
  
               BUFOUT(IX,IY) = QUADRI(XOLD, YOLD, NX, NY, XIMG)
            ENDDO

         ENDDO
c$omp    end parallel do

         IRTFLG = 0

         END


C******************************** RTSQ_PAD *****************************

         SUBROUTINE RTSQ_PAD(XIMG,BUFOUT, NX,NY, NXP,NYP,
     &                     THETA,SCLI,SHXI,SHYI, IRTFLG)

         IMPLICIT NONE
         REAL            :: XIMG(NX,NY)
         REAL            :: BUFOUT(NXP,NYP)   
         INTEGER         :: NX,NY, NXP,NYP
         REAL            :: THETA,SCLI,SHXI,SHYI
         INTEGER         :: IRTFLG

	 REAL, PARAMETER :: QUADPI = 3.14159265358979323846
	 REAL, PARAMETER :: DGR_TO_RAD = (QUADPI/180)

         REAL            :: SHX,SHY,RY1,RX1,RY2,RX2,COD,SID,XI
         REAL            :: CODDSCLI,SIDDSCLI,FIXCENMSHX,FIYCENMSHY 
         REAL            :: RYE2,RYE1,RXE2,RXE1,YI
         REAL            :: YCOD,YSID,YOLD,XOLD
         INTEGER         :: IYCEN,IXCEN,IX,IY

         REAL            :: quadri

C        SHIFT WITHIN IMAGE BOUNDARY
         SHX   = AMOD(SHXI,FLOAT(NX))
         SHY   = AMOD(SHYI,FLOAT(NY))

C        SPIDER IMAGE CENTER
         IYCEN = NY/2+1
         IXCEN = NX/2+1

C        IMAGE DIMENSIONS AROUND ORIGIN
         RX1   = -NX/2
         RX2   =  NX/2
         RY1   = -NY/2
         RY2   =  NY/2

         IF (MOD(NX,2) == 0) THEN
            RX2  =  RX2 - 1.0
            RXE1 = -NX
            RXE2 =  NX
         ELSE
            RXE1 = -NX - 1
            RXE2 =  NX + 1
         ENDIF

         IF (MOD(NY,2) == 0) THEN
            RY2  =  RY2 - 1.0
            RYE1 = -NY 
            RYE2 =  NY
         ELSE
            RYE1 = -NY - 1
            RYE2 =  NY + 1

         ENDIF

C        CREATE TRANSFORMATION MATRIX
         COD = COS(THETA * DGR_TO_RAD)
         SID = SIN(THETA * DGR_TO_RAD)

C        ADJUST FOR SCALING
         CODDSCLI = COD / SCLI
         SIDDSCLI = SID / SCLI

C        -(CENTER PLUS SHIFT)
         FIXCENMSHX = -IXCEN - SHX
         FIYCENMSHY = -IYCEN - SHY

c$omp    parallel do private(iy,yi,ycod,ysid, ix,xi,xold,yold)
         DO IY=1,NY

            YI = IY + FIYCENMSHY
            IF (YI < RY1) YI = MIN(YI+RYE2, RY2)
            IF (YI > RY2) YI = MAX(YI+RYE1, RY1)

            YCOD =  YI * CODDSCLI + IYCEN
            YSID = -YI * SIDDSCLI + IXCEN

            DO IX=1,NX
               XI = IX + FIXCENMSHX                           
               IF (XI  <  RX1) XI = MIN(XI+RXE2, RX2)   
               IF (XI  >  RX2) XI = MAX(XI+RXE1, RX1) 
 
               YOLD          = XI * SIDDSCLI + YCOD  
               XOLD          = XI * CODDSCLI + YSID  
               BUFOUT(IX,IY) = QUADRI(XOLD, YOLD, NX, NY, XIMG)
            ENDDO
         ENDDO

         IRTFLG = 0
         END




