
    module TB_SmoothSwitches
!---^^^^^^^^^^^^^^^^^^^^^^^^
!*      This module defines a very smooth polynomial switching function
!*      of 9th order for which at the taper point rt the first 4 derivatives are zero and the value is one.
!*      The value and first 4 derivatives are zero at the cutoff point rc.
!*      Thus the function f(r) may be smoothly truncated by multiplying with p(r)
!*
!*              f(r)p(r)        =       {   f(r)                    r <= r_t
!*                                      {   0 < f(r)p(r) < f(r)     r_t < r < r_c
!*                                      {   0                       r >= r_c
!*      See also:
!*      D.R. Mason, W.M.C. Foulkes, and A.P. Sutton
!*      Phil. Mag. Lett. 90 (2010) 51-60

!*      Author      :   Daniel Mason
!*      Version     :   1.0
!*      Revision    :   Feb 2011

        implicit none
        private

    !---

        public      ::      SmoothSwitch_ctor
        public      ::      report
        public      ::      delete

        public      ::      switch                  !   find tapered function
        public      ::      switchDerivative        !   find derivative of tapered function
        public      ::      switchSecondDerivative  !   find second derivative of tapered function

        public      ::      getTaper
        public      ::      getCutoff
        public      ::      inRange


    !---    private static fields: the polynomial coefficients needed
        real(kind=8),private,parameter        ::      AA =  126.0d0
        real(kind=8),private,parameter        ::      BB = -420.0d0
        real(kind=8),private,parameter        ::      CC =  540.0d0
        real(kind=8),private,parameter        ::      DD = -315.0d0
        real(kind=8),private,parameter        ::      EE =   70.0d0

    !---

        type,public         ::      SmoothSwitch
            private
            real(kind=8)            ::      taper
            real(kind=8)            ::      cutoff
            real(kind=8)            ::      irange
        end type SmoothSwitch

    !---

        interface       SmoothSwitch_ctor
            module procedure        SmoothSwitch_null
            module procedure        SmoothSwitch_ctor0
        end interface

        interface       report
            module procedure        report_SS
        end interface

        interface       delete
            module procedure        delete_SS
        end interface


        interface       switch
            module procedure        switch_SS
            module procedure        switch_SS1
            module procedure        switch_SS2
        end interface

        interface       switchDerivative
            module procedure        switchDerivative_SS
            module procedure        switchDerivative_SS1
            module procedure        switchDerivative_SS2
        end interface

        interface       switchSecondDerivative
            module procedure        switchSecondDerivative_SS
            module procedure        switchSecondDerivative_SS1
            module procedure        switchSecondDerivative_SS2
        end interface


        interface       getTaper
            module procedure    getTaper_SS
        end interface

        interface       getCutoff
            module procedure    getCutoff_SS
        end interface

        interface       inRange
            module procedure    inRange_SS
        end interface


    contains
!---^^^^^^^^

        pure function SmoothSwitch_null() result(this)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      constructs a new empty switch - always returns 1.
            type(SmoothSwitch)      ::      this
            this = SmoothSwitch_ctor0(1.0d12,1.0d13)
            return
        end function SmoothSwitch_null

        pure function SmoothSwitch_ctor0(rt,rc) result(this)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      constructs a new switch from taper rt to cutoff rc
            real(kind=8),intent(in)                 ::      rt,rc
            type(SmoothSwitch)      ::      this
            this%taper = rt
            this%cutoff = rc
            if (rc>rt*1.00001d0) then
                this%irange = 1.0d0/(rc-rt)
            else
                this%irange = 0.0d0
            end if
            return
        end function SmoothSwitch_ctor0

        subroutine delete_SS(this)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      Would deallocate dynamic memory, but there isn't any, so does nothing.
            type(SmoothSwitch),intent(inout)      ::      this
            return
        end subroutine delete_SS

        subroutine report_SS(this,u)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            type(SmoothSwitch),intent(in)       ::      this
            integer,intent(in),optional         ::      u
            integer         ::      uu
            uu = 6
            if(present(u)) uu = u
            write (unit=uu,fmt='(a)')           "SmoothSwitch"
            write (unit=uu,fmt='(a,2f16.8)')    "  taper,cutoff    : ",this%taper,this%cutoff
            return
        end subroutine report_SS

!-------

        pure function switch_SS(this,x,y,squared) result(yprime)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns value of switched function at x.
    !*      y is the value it would be if switch not applied
    !*      if squared then x is actually distance squared
            type(SmoothSwitch),intent(in)       ::      this
            real(kind=8),intent(in)                     ::      x
            real(kind=8),intent(in)                     ::      y
            logical,intent(in),optional         ::      squared
            real(kind=8)                                ::      yprime
            real(kind=8)        ::      zz,pp
            logical     ::      sq
            yprime = 0.0d0
            sq = .false.
            if (present(squared)) sq = squared
            if (sq) then
                if (x < this%taper*this%taper) then
                    yprime = y
                else if (x < this%cutoff*this%cutoff) then
                    zz = (this%cutoff - sqrt(x))*this%irange
                    pp = ( AA + zz*(BB + zz*(CC + zz*(DD + zz*EE))) )*(zz*zz)*(zz*zz)*zz
                    yprime = y*pp
                end if
            else
                if (x < this%taper) then
                    yprime = y
                else if (x < this%cutoff) then
                    zz = (this%cutoff - x)*this%irange
                    pp = ( AA + zz*(BB + zz*(CC + zz*(DD + zz*EE))) )*(zz*zz)*(zz*zz)*zz
                    yprime = y*pp
                end if
            end if
            return
        end function switch_SS

        pure function switch_SS1(this,x,y,squared) result(yprime)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns value of switched function at x.
    !*      y is the value it would be if switch not applied
    !*      if squared then x is actually distance squared.
    !*      This version works on an array of function values y(:)
            type(SmoothSwitch),intent(in)       ::      this
            real(kind=8),intent(in)                     ::      x
            real(kind=8),dimension(:),intent(in)        ::      y
            logical,intent(in),optional         ::      squared
            real(kind=8),dimension(size(y))             ::      yprime
            real(kind=8)        ::      zz,pp
            logical     ::      sq
            yprime = 0.0d0
            sq = .false.
            if (present(squared)) sq = squared
            if (sq) then
                if (x < this%taper*this%taper) then
                    yprime = y
                else if (x < this%cutoff*this%cutoff) then
                    zz = (this%cutoff - sqrt(x))*this%irange
                    pp = ( AA + zz*(BB + zz*(CC + zz*(DD + zz*EE))) )*(zz*zz)*(zz*zz)*zz
                    yprime = y*pp
                end if
            else
                if (x < this%taper) then
                    yprime = y
                else if (x < this%cutoff) then
                    zz = (this%cutoff - x)*this%irange
                    pp = ( AA + zz*(BB + zz*(CC + zz*(DD + zz*EE))) )*(zz*zz)*(zz*zz)*zz
                    yprime = y*pp
                end if
            end if
            return
        end function switch_SS1

        pure function switch_SS2(this,x,y,squared) result(yprime)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns value of switched function at x.
    !*      y is the value it would be if switch not applied
    !*      if squared then x is actually distance squared
    !*      This version works on an array of function values y(:,:)

            type(SmoothSwitch),intent(in)       ::      this
            real(kind=8),intent(in)                     ::      x
            real(kind=8),dimension(:,:),intent(in)      ::      y
            logical,intent(in),optional         ::      squared
            real(kind=8),dimension(size(y,dim=1),size(y,dim=2))     ::      yprime
            real(kind=8)        ::      zz,pp
            logical     ::      sq
            yprime = 0.0d0
            sq = .false.
            if (present(squared)) sq = squared
            if (sq) then
                if (x < this%taper*this%taper) then
                    yprime = y
                else if (x < this%cutoff*this%cutoff) then
                    zz = (this%cutoff - sqrt(x))*this%irange
                    pp = ( AA + zz*(BB + zz*(CC + zz*(DD + zz*EE))) )*(zz*zz)*(zz*zz)*zz
                    yprime = y*pp
                end if
            else
                if (x < this%taper) then
                    yprime = y
                else if (x < this%cutoff) then
                    zz = (this%cutoff - x)*this%irange
                    pp = ( AA + zz*(BB + zz*(CC + zz*(DD + zz*EE))) )*(zz*zz)*(zz*zz)*zz
                    yprime = y*pp
                end if
            end if
            return
        end function switch_SS2

!-------

        pure function switchDerivative_SS(this,x,y,dy,squared) result(dyprime)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns value of derivative of switched function at x.
    !*      y is the value of the function and dy the derivative if switch not applied
    !*      if squared then x is actually distance squared

            type(SmoothSwitch),intent(in)       ::      this
            real(kind=8),intent(in)                     ::      x
            real(kind=8),intent(in)                     ::      y,dy
            logical,intent(in),optional         ::      squared
            real(kind=8)                                ::      dyprime
            real(kind=8)        ::      zz,pp,dpp
            logical     ::      sq
            dyprime = 0.0d0
            sq = .false.
            if (present(squared)) sq = squared
            if (sq) then
                if (x < this%taper*this%taper) then
                    dyprime = dy
                else if (x < this%cutoff*this%cutoff) then
                    zz = (this%cutoff - sqrt(x))*this%irange
                    pp = ( AA + zz*(BB + zz*(CC + zz*(DD + zz*EE))) )*(zz*zz)*(zz*zz)*zz
                    dpp = ( 5*AA + zz*(6*BB + zz*(7*CC + zz*(8*DD + zz*9*EE))) )*(zz*zz)*(zz*zz)*(-this%irange)
                    dyprime = y*dpp + dy*pp
                end if
            else
                if (x < this%taper) then
                    dyprime = dy
                else if (x < this%cutoff) then
                    zz = (this%cutoff - x)*this%irange
                    pp = ( AA + zz*(BB + zz*(CC + zz*(DD + zz*EE))) )*(zz*zz)*(zz*zz)*zz
                    dpp = ( 5*AA + zz*(6*BB + zz*(7*CC + zz*(8*DD + zz*9*EE))) )*(zz*zz)*(zz*zz)*(-this%irange)
                    dyprime = y*dpp + dy*pp
                end if
            end if
            return
        end function switchDerivative_SS


        pure function switchDerivative_SS1(this,x,y,dy,squared) result(dyprime)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns value of derivative of switched function at x.
    !*      y is the value of the function and dy the derivative if switch not applied
    !*      if squared then x is actually distance squared
    !*      This version works on an array of function values y(:),dy(:)

            type(SmoothSwitch),intent(in)       ::      this
            real(kind=8),intent(in)                     ::      x
            real(kind=8),dimension(:),intent(in)        ::      y,dy
            logical,intent(in),optional         ::      squared
            real(kind=8),dimension(size(y))             ::      dyprime
            real(kind=8)        ::      zz,pp,dpp
            logical     ::      sq
            dyprime = 0.0d0
            sq = .false.
            if (present(squared)) sq = squared
            if (sq) then
                if (x < this%taper*this%taper) then
                    dyprime = dy
                else if (x < this%cutoff*this%cutoff) then
                    zz = (this%cutoff - sqrt(x))*this%irange
                    pp = ( AA + zz*(BB + zz*(CC + zz*(DD + zz*EE))) )*(zz*zz)*(zz*zz)*zz
                    dpp = ( 5*AA + zz*(6*BB + zz*(7*CC + zz*(8*DD + zz*9*EE))) )*(zz*zz)*(zz*zz)*(-this%irange)
                    dyprime = y*dpp + dy*pp
                end if
            else
                if (x < this%taper) then
                    dyprime = dy
                else if (x < this%cutoff) then
                    zz = (this%cutoff - x)*this%irange
                    pp = ( AA + zz*(BB + zz*(CC + zz*(DD + zz*EE))) )*(zz*zz)*(zz*zz)*zz
                    dpp = ( 5*AA + zz*(6*BB + zz*(7*CC + zz*(8*DD + zz*9*EE))) )*(zz*zz)*(zz*zz)*(-this%irange)
                    dyprime = y*dpp + dy*pp
                end if
            end if
            return
        end function switchDerivative_SS1


        pure function switchDerivative_SS2(this,x,y,dy,squared) result(dyprime)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns value of derivative of switched function at x.
    !*      y is the value of the function and dy the derivative if switch not applied
    !*      if squared then x is actually distance squared
    !*      This version works on an array of function values y(:,:),dy(:,:)
            type(SmoothSwitch),intent(in)       ::      this
            real(kind=8),intent(in)                     ::      x
            real(kind=8),dimension(:,:),intent(in)      ::      y,dy
            logical,intent(in),optional         ::      squared
            real(kind=8),dimension(size(y,dim=1),size(y,dim=2))     ::      dyprime
            real(kind=8)        ::      zz,pp,dpp
            logical     ::      sq
            dyprime = 0.0d0
            sq = .false.
            if (present(squared)) sq = squared
            if (sq) then
                if (x < this%taper*this%taper) then
                    dyprime = dy
                else if (x < this%cutoff*this%cutoff) then
                    zz = (this%cutoff - sqrt(x))*this%irange
                    pp = ( AA + zz*(BB + zz*(CC + zz*(DD + zz*EE))) )*(zz*zz)*(zz*zz)*zz
                    dpp = ( 5*AA + zz*(6*BB + zz*(7*CC + zz*(8*DD + zz*9*EE))) )*(zz*zz)*(zz*zz)*(-this%irange)
                    dyprime = y*dpp + dy*pp
                end if
            else
                if (x < this%taper) then
                    dyprime = dy
                else if (x < this%cutoff) then
                    zz = (this%cutoff - x)*this%irange
                    pp = ( AA + zz*(BB + zz*(CC + zz*(DD + zz*EE))) )*(zz*zz)*(zz*zz)*zz
                    dpp = ( 5*AA + zz*(6*BB + zz*(7*CC + zz*(8*DD + zz*9*EE))) )*(zz*zz)*(zz*zz)*(-this%irange)
                    dyprime = y*dpp + dy*pp
                end if
            end if
            return
        end function switchDerivative_SS2


!-------

        pure function switchSecondDerivative_SS(this,x,y,dy,d2y) result(d2yprime)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns value of 2nd derivative of switched function at x.
    !*      y is the value of the function and dy the derivative,
    !*      d2y the 2nd deriv if switch not applied
            type(SmoothSwitch),intent(in)       ::      this
            real(kind=8),intent(in)                     ::      x
            real(kind=8),intent(in)                     ::      y,dy,d2y
            real(kind=8)                                ::      d2yprime
            real(kind=8)        ::      zz,pp,dpp,d2pp
            d2yprime = 0.0d0
            if (x < this%taper) then
                d2yprime = d2y
            else if (x < this%cutoff) then
                zz = (this%cutoff - x)*this%irange
                pp = ( AA + zz*(BB + zz*(CC + zz*(DD + zz*EE))) )*(zz*zz)*(zz*zz)*zz
                dpp = ( 5*AA + zz*(6*BB + zz*(7*CC + zz*(8*DD + zz*9*EE))) )*(zz*zz)*(zz*zz)*(-this%irange)
                d2pp = ( 20*AA + zz*(30*BB + zz*(42*CC + zz*(56*DD + zz*72*EE))) )*(zz*zz)*zz*(this%irange*this%irange)
                d2yprime = y*d2pp + 2*dy*dpp + d2y*pp
            end if
            return
        end function switchSecondDerivative_SS

        pure function switchSecondDerivative_SS1(this,x,y,dy,d2y) result(d2yprime)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns value of 2nd derivative of switched function at x.
    !*      y is the value of the function and dy the derivative, d2y the 2nd deriv if switch not applied
            type(SmoothSwitch),intent(in)       ::      this
            real(kind=8),intent(in)                     ::      x
            real(kind=8),dimension(:),intent(in)        ::      y,dy,d2y
            real(kind=8),dimension(size(y))             ::      d2yprime
            real(kind=8)        ::      zz,pp,dpp,d2pp
            d2yprime = 0.0d0
            if (x < this%taper) then
                d2yprime = d2y
            else if (x < this%cutoff) then
                zz = (this%cutoff - x)*this%irange
                pp = ( AA + zz*(BB + zz*(CC + zz*(DD + zz*EE))) )*(zz*zz)*(zz*zz)*zz
                dpp = ( 5*AA + zz*(6*BB + zz*(7*CC + zz*(8*DD + zz*9*EE))) )*(zz*zz)*(zz*zz)*(-this%irange)
                d2pp = ( 20*AA + zz*(30*BB + zz*(42*CC + zz*(56*DD + zz*72*EE))) )*(zz*zz)*zz*(this%irange*this%irange)
                d2yprime = y*d2pp + 2*dy*dpp + d2y*pp
            end if
            return
        end function switchSecondDerivative_SS1

        pure function switchSecondDerivative_SS2(this,x,y,dy,d2y) result(d2yprime)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns value of 2nd derivative of switched function at x.
    !*      y is the value of the function and dy the derivative, d2y the 2nd deriv if switch not applied
            type(SmoothSwitch),intent(in)       ::      this
            real(kind=8),intent(in)                     ::      x
            real(kind=8),dimension(:,:),intent(in)      ::      y,dy,d2y
            real(kind=8),dimension(size(y,dim=1),size(y,dim=2))     ::      d2yprime
            real(kind=8)        ::      zz,pp,dpp,d2pp
            d2yprime = 0.0d0
            if (x < this%taper) then
                d2yprime = d2y
            else if (x < this%cutoff) then
                zz = (this%cutoff - x)*this%irange
                pp = ( AA + zz*(BB + zz*(CC + zz*(DD + zz*EE))) )*(zz*zz)*(zz*zz)*zz
                dpp = ( 5*AA + zz*(6*BB + zz*(7*CC + zz*(8*DD + zz*9*EE))) )*(zz*zz)*(zz*zz)*(-this%irange)
                d2pp = ( 20*AA + zz*(30*BB + zz*(42*CC + zz*(56*DD + zz*72*EE))) )*(zz*zz)*zz*(this%irange*this%irange)
                d2yprime = y*d2pp + 2*dy*dpp + d2y*pp
            end if
            return
        end function switchSecondDerivative_SS2

!-------

        pure function getTaper_SS(this) result(rt)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns taper range
            type(SmoothSwitch),intent(in)       ::      this
            real(kind=8)                                ::      rt
            rt = this%taper
            return
        end function getTaper_SS


        pure function getCutoff_SS(this) result(rc)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns cutoff range
            type(SmoothSwitch),intent(in)       ::      this
            real(kind=8)                                ::      rc
            rc = this%cutoff
            return
        end function getCutoff_SS

        elemental function inRange_SS(this,r,squared) result(is)
    !---^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    !*      returns true if r is within cutoff range
            type(SmoothSwitch),intent(in)       ::      this
            real(kind=8),intent(in)                     ::      r
            logical,intent(in),optional         ::      squared
            logical                             ::      is
            if (present(squared)) then
                if (squared) then
                    is = ( r <= this%cutoff*this%cutoff )
                else
                    is = r <= this%cutoff
                end if
            else
                is = r <= this%cutoff
            end if
            return
        end function inRange_SS




    end module TB_SmoothSwitches

!     program testSmoothSwitches
! !---^^^^^^^^^^^^^^^^^^^^^^^^^^

!         use TB_SmoothSwitches
!         implicit none
!
!         type(SmoothSwitch)      ::      sw
!         integer                 ::      ii
!         real(kind=8)                    ::      theta
!         real(kind=8)                    ::      f,df,d2f
!         real(kind=8)                    ::      g,dg,d2g
!
!         sw = SmoothSwitch_ctor( 5.0,6.0 )
!
!         do ii = 0,1000
!             theta = ii*0.001*2*3.141592654
!             f = switch( sw,theta, cos(theta) )
!             df = switchDerivative( sw,theta, cos(theta),-sin(theta) )
!             d2f = switchSecondDerivative( sw,theta, cos(theta),-sin(theta),-cos(theta) )
!             g = switch( sw,theta, 1.0 )
!             dg = switchDerivative( sw,theta, 1.0,0.0 )
!             d2g = switchSecondDerivative( sw,theta, 1.0,0.0,0.0 )
!             write (*,fmt='(100f16.8)') theta,cos(theta),-sin(theta),-cos(theta),f,df,d2f,g,dg,d2g
!         end do
!
!     end program testSmoothSwitches

